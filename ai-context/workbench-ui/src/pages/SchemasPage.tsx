import { Database } from "lucide-react";
import PageHeader from "../components/common/PageHeader";
import { Schemas } from "../components/schemas/Schemas";

const SchemasPage = () => {
  return (
    <>
      <PageHeader
        icon={<Database />}
        title="Schema Management"
        description="Define and manage data schemas for your knowledge graph"
      />
      <Schemas />
    </>
  );
};

export default SchemasPage;
