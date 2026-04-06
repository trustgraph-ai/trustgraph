import React from "react";

import { Search as SearchIcon } from "lucide-react";

import Search from "../components/search/Search";
import PageHeader from "../components/common/PageHeader";

const SearchPage = () => {
  return (
    <>
      <PageHeader
        icon={<SearchIcon />}
        title="Document search"
        description="Semantic matching against entities in the knowledge graph"
      />
      <Search />
    </>
  );
};

export default SearchPage;
