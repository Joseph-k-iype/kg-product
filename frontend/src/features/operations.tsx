import { useData } from "@/api/client";
import {
  PageTitle,
  Block,
  Status,
  ErrorState,
  Loading,
} from "@/components/shared";

export function Operations() {
  const { data, error, loading } = useData<{
    probes: Record<string, string>;
    identity_mode: string;
  }>("/health", 5000);
  return (
    <>
      <PageTitle
        eyebrow="OPERATIONS"
        title="Service status"
        description="Technical details for workspace administrators."
      />
      <Block title="Local services">
        {error ? (
          <ErrorState message={error} />
        ) : loading ? (
          <Loading />
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Service</th>
                  <th>Connection</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(data?.probes || {}).map(([name, state]) => (
                  <tr key={name}>
                    <td>
                      {name === "postgres"
                        ? "PostgreSQL with pgvector"
                        : name === "minio"
                          ? "MinIO object storage"
                          : "FalkorDB instance storage"}
                    </td>
                    <td>
                      <Status
                        value={state === "ready" ? "ready" : "failed"}
                        label={state}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Block>
      <div className="guidance">
        This local application uses synthetic identities. It does not implement
        production authentication. RDF definitions are stored as versioned
        files; unrestricted reasoning and a remote SPARQL endpoint are not
        enabled.
      </div>
    </>
  );
}
