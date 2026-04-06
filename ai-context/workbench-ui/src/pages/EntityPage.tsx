import { Waypoints } from "lucide-react";

import PageHeader from "../components/common/PageHeader";
import EntityDetail from "../components/entity/EntityDetail";

const EntityPage = () => {
  return (
    <>
      <PageHeader
        icon={<Waypoints />}
        title="Explore"
        description="Exploring properties and relationships of the knowledge graph"
      />
      <EntityDetail />
    </>
  );
};

export default EntityPage;
