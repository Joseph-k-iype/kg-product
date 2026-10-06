from fastapi import HTTPException
from sqlalchemy import select, func
from app.features.products.models import Product, Revision, Activity

def require(session, model, id):
    item = session.get(model, str(id))
    if not item:
        raise HTTPException(404, {'code':'not_found','message':'Record not found'})
    return item

def revision(session, product_id, revision_id=None, lock=False):
    query = select(Revision).where(Revision.product_id == str(product_id))
    if revision_id:
        query = query.where(Revision.id == str(revision_id))
    else:
        query = query.where(Revision.state != 'published').order_by(Revision.number.desc())
    if lock:
        query = query.with_for_update()
    result = session.scalars(query).first()
    if not result:
        raise HTTPException(409, {'code':'draft_required','message':'Open a draft to make changes'})
    return result

def mutable(rev):
    if rev.state == 'published':
        raise HTTPException(409, {'code':'immutable_release','message':'Published knowledge is read-only. Open a draft.'})

def touch(session, rev, action, expected=None):
    mutable(rev)
    if expected is not None and expected != rev.generation:
        raise HTTPException(409, {'code':'generation_conflict','message':'This draft changed. Refresh before saving.'})
    rev.generation += 1
    rev.state = 'draft'
    rev.graph_build_id = None
    session.add(Activity(product_id=rev.product_id,revision_id=rev.id,action=action))
    # Dependent evidence is invalidated by captured generation; no historical rows are deleted.

def detail(session, product):
    revs = session.scalars(select(Revision).where(Revision.product_id == product.id).order_by(Revision.number.desc())).all()
    drafts = [r for r in revs if r.state != 'published']
    def rd(r):
        return {'id':r.id,'number':r.number,'generation':r.generation,'state':r.state,'config':r.config,
                'ontology_id':r.ontology_id,'mapping_id':r.mapping_id,'graph_build_id':r.graph_build_id}
    return {'id':product.id,'name':product.name,'purpose':product.purpose,'domain':product.domain,'owner':product.owner,
            'tags':product.tags,'active_release_id':product.active_release_id,'draft':rd(drafts[0]) if drafts else None,
            'revisions':[rd(r) for r in revs],'created_at':product.created_at}

def create_product(session, input):
    product = Product(**input.model_dump(exclude={'config'}))
    session.add(product); session.flush()
    rev = Revision(product_id=product.id,number=1,config=input.config)
    session.add(rev); session.flush()
    session.add(Activity(product_id=product.id,revision_id=rev.id,action='Draft created'))
    return detail(session, product)

def update_draft(session, product_id, input):
    product = session.scalars(select(Product).where(Product.id == str(product_id)).with_for_update()).first()
    if not product:
        require(session, Product, product_id)
    rev = revision(session,product.id,lock=True)
    touch(session,rev,'Product details updated',input.expected_generation)
    for key,value in input.model_dump(exclude={'expected_generation'},exclude_none=True).items():
        if key == 'config': rev.config = value
        else: setattr(product,key,value)
    session.flush()
    return detail(session,product)

def open_draft(session, product_id):
    product = require(session,Product,product_id)
    session.execute(select(Product).where(Product.id == product.id).with_for_update())
    existing = session.scalars(select(Revision).where(Revision.product_id == product.id,Revision.state != 'published')).first()
    if existing:
        return detail(session,product)
    latest = session.scalars(select(Revision).where(Revision.product_id == product.id).order_by(Revision.number.desc())).first()
    rev = Revision(product_id=product.id,number=latest.number+1,config=latest.config.copy(),ontology_id=latest.ontology_id,mapping_id=latest.mapping_id)
    session.add(rev); session.flush()
    # Later feature owns the document snapshot copy on new draft.
    session.add(Activity(product_id=product.id,revision_id=rev.id,action='New draft opened'))
    return detail(session,product)

def catalog(session,q='',domain='',owner='',state='',sort='name',offset=0,limit=50):
    query = select(Product)
    if q: query = query.where(Product.name.ilike(f'%{q}%'))
    if domain: query = query.where(Product.domain == domain)
    if owner: query = query.where(Product.owner == owner)
    if state == 'published': query = query.where(Product.active_release_id.is_not(None))
    if state == 'draft': query = query.where(Product.active_release_id.is_(None))
    total = session.scalar(select(func.count()).select_from(query.subquery()))
    query = query.order_by(Product.created_at.desc() if sort == 'recent' else Product.name).offset(offset).limit(limit)
    return {'items':[detail(session,p) for p in session.scalars(query)],'total':total,'offset':offset,'limit':limit}
