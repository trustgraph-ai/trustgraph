import React from "react";
import { LibraryBig } from "lucide-react";
import { Tabs } from "@chakra-ui/react";

import PageHeader from "../components/common/PageHeader";
import Documents from "../components/library/Documents";
import Collections from "../components/library/Collections";

const LibraryPage = () => {
  return (
    <>
      <PageHeader
        icon={<LibraryBig />}
        title="Library"
        description="Managing documents and collections"
      />
      <Tabs.Root defaultValue="documents">
        <Tabs.List>
          <Tabs.Trigger value="documents">Documents</Tabs.Trigger>
          <Tabs.Trigger value="collections">Collections</Tabs.Trigger>
        </Tabs.List>
        <Tabs.Content value="documents">
          <Documents />
        </Tabs.Content>
        <Tabs.Content value="collections">
          <Collections />
        </Tabs.Content>
      </Tabs.Root>
    </>
  );
};

export default LibraryPage;
