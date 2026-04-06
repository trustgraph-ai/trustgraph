import React from "react";
import { HStack, Input } from "@chakra-ui/react";

interface OntologyTreeSearchProps {
  searchTerm: string;
  onSearchChange: (searchTerm: string) => void;
}

export const OntologyTreeSearch: React.FC<OntologyTreeSearchProps> = ({
  searchTerm,
  onSearchChange,
}) => {
  return (
    <HStack>
      <Input
        placeholder="🔍 Search concepts..."
        value={searchTerm}
        onChange={(e) => onSearchChange(e.target.value)}
      />
    </HStack>
  );
};
