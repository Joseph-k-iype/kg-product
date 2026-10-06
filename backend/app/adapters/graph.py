import json,re
from redis import Redis
from app.config import settings

class GraphAdapter:
    def __init__(self):self.client=Redis.from_url(settings.graph_url,decode_responses=True,socket_timeout=15)
    def query(self,key,query,params=None,read_only=True):
        if params:query='CYPHER '+' '.join(k+'='+json.dumps(v,ensure_ascii=True) for k,v in params.items())+' '+query
        result=self.client.execute_command('GRAPH.RO_QUERY' if read_only else 'GRAPH.QUERY',key,query)
        return result[1] if len(result)>1 else []
    def build(self,build):
        for node in build.instances:
            label=node['type']
            if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*',label):raise ValueError('Invalid fact type')
            self.query(build.graph_key,f'MERGE (n:{label} {{id:$id}}) SET n.type=$type,n.label=$label,n.iri=$iri,n.attributes=$attributes,n.evidence=$evidence,n.extraction_version=$version',
                {'id':node['id'],'type':label,'label':node['label'],'iri':node['iri'],'attributes':json.dumps(node['attributes']),'evidence':json.dumps(node['evidence']),'version':build.extraction_version},False)
        for edge in build.relationships:
            type=edge['type']
            if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*',type):raise ValueError('Invalid relationship type')
            self.query(build.graph_key,f'MATCH (a {{id:$source}}),(b {{id:$target}}) MERGE (a)-[r:{type}]->(b) SET r.evidence=$evidence',{'source':edge['source'],'target':edge['target'],'evidence':json.dumps(edge['evidence'])},False)
        self.verify(build)
    def verify(self,build):
        count=self.query(build.graph_key,'MATCH (n) RETURN count(n)')[0][0]
        if int(count)!=len(build.instances):raise ValueError('Fact build is incomplete')
    def search(self,build,query='',entity_type=None,limit=50):
        limit=max(1,min(int(limit),200))
        rows=self.query(build.graph_key,f'MATCH (n) WHERE (toLower(n.label) CONTAINS toLower($query) OR toLower(n.id) CONTAINS toLower($query)) AND ($type="" OR n.type=$type) RETURN n.id,n.type,n.label,n.iri,n.attributes,n.evidence ORDER BY n.label LIMIT {limit}',{'query':query,'type':entity_type or ''})
        return [{'id':r[0],'type':r[1],'label':r[2],'iri':r[3],'attributes':json.loads(r[4]),'evidence':json.loads(r[5]),'build_id':build.id,'extraction_version':build.extraction_version,'provenance_label':'Fixture-backed extraction'} for r in rows]
    def neighbors(self,build,entity_id,limit=20):
        limit=max(1,min(int(limit),50))
        root=self.search(build,entity_id,None,1)
        rows=self.query(build.graph_key,f'MATCH (a {{id:$id}})-[r]-(b) RETURN b.id,type(r),startNode(r).id,endNode(r).id,r.evidence LIMIT {max(0,limit-1)}',{'id':entity_id})
        nodes=root[:1];edges=[]
        for row in rows:
            match=self.search(build,row[0],None,1)
            if match and all(n['id']!=match[0]['id'] for n in nodes):nodes+=match
            edges.append({'source':row[2],'target':row[3],'type':row[1],'evidence':json.loads(row[4])})
        return {'nodes':nodes,'relationships':edges}
