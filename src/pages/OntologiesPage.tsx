import React from "react";
import { Tags } from "lucide-react";
import PageHeader from "../components/common/PageHeader";
import { Ontologies } from "../components/ontologies/Ontologies";

const OntologiesPage: React.FC = () => {
  return (
    <>
      <PageHeader
        icon={<Tags />}
        title="Ontology Management"
        description="Create and manage ontologies for knowledge management"
      />
      <Ontologies />
    </>
  );
};

export default OntologiesPage;
