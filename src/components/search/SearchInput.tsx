import React from "react";

// Chakra UI components for form input and layout
import { Input, HStack } from "@chakra-ui/react";

// State management hooks
import { useProgressStateStore } from "@trustgraph/react-state";
import { useSearchStateStore } from "@trustgraph/react-state";
// Child components
import SearchHelp from "./SearchHelp";
import ProgressSubmitButton from "../common/ProgressSubmitButton";

/**
 * SearchInput component provides the search interface with input field and
 * submit button
 * Handles user input, form submission, and keyboard shortcuts
 * Integrates with progress state to show loading states
 */
const SearchInput = ({ submit }) => {
  // Get current activity state to disable input during processing
  const activity = useProgressStateStore((state) => state.activity);

  // Get current search input value and setter from search state
  const search = useSearchStateStore((state) => state.input);
  const setSearch = useSearchStateStore((state) => state.setInput);

  /**
   * Handles keyboard shortcuts for form submission
   * Submits the search when Enter key is pressed
   */
  const handleKeyDown = (e) => {
    if (["Enter"].includes(e.key)) {
      e.preventDefault();
      submit();
    }
  };

  return (
    <>
      <form onSubmit={submit}>
        <HStack>
          {/* Main search input field */}
          <Input
            variant="outline"
            placeholder="Perform a vector search on a term or phrase..."
            value={search}
            onKeyDown={handleKeyDown}
            onChange={(e) => {
              // Update search input in state as user types
              setSearch(e.target.value);
            }}
          />

          {/* Submit button with progress indication */}
          <ProgressSubmitButton
            disabled={activity.size > 0}
            working={activity.size > 0}
            onClick={() => submit()}
          />

          {/* Help button that shows search instructions */}
          <SearchHelp />
        </HStack>
      </form>
    </>
  );
};

export default SearchInput;
