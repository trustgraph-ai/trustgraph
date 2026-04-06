import React, { useState, useMemo } from "react";
import { VStack, HStack, Button, Textarea, Text, Box } from "@chakra-ui/react";
import { Play } from "lucide-react";
import { useObjectsQuery } from "@trustgraph/react-state";
import {
  createColumnHelper,
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
} from "@tanstack/react-table";
import BasicTable from "../common/BasicTable";

// Dynamic table row type for GraphQL results
type GraphQLResultRow = Record<string, unknown>;

const columnHelper = createColumnHelper<GraphQLResultRow>();

const RunGraphQLTab: React.FC = () => {
  const [query, setQuery] = useState("");
  const objectsQuery = useObjectsQuery();

  const handleSubmit = () => {
    if (!query.trim()) return;

    objectsQuery.executeQuery({ query: query.trim() });
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && e.ctrlKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  // Dynamically create columns based on the first row of results
  const { columns, tableData } = useMemo(() => {
    if (!objectsQuery.data?.data) {
      return { columns: [], tableData: [] };
    }

    // Extract the first array of results from the GraphQL response
    // GraphQL responses typically have structure like { data: { users: [...] } }
    const dataKeys = Object.keys(objectsQuery.data.data);
    if (dataKeys.length === 0) {
      return { columns: [], tableData: [] };
    }

    // Get the first data collection
    const firstKey = dataKeys[0];
    const results = objectsQuery.data.data[firstKey];

    if (!Array.isArray(results) || results.length === 0) {
      return { columns: [], tableData: [] };
    }

    // Create columns based on the keys of the first result object
    const sampleRow = results[0];
    const resultColumns = Object.keys(sampleRow).map((key) =>
      columnHelper.accessor(key, {
        header: key.charAt(0).toUpperCase() + key.slice(1),
        cell: (info) => {
          const value = info.getValue();

          // Handle different value types
          if (value === null || value === undefined) {
            return <Text color="fg.muted">—</Text>;
          }

          if (typeof value === "object") {
            return (
              <Text fontSize="sm" fontFamily="mono">
                {JSON.stringify(value, null, 2)}
              </Text>
            );
          }

          if (typeof value === "boolean") {
            return (
              <Text color={value ? "green.500" : "red.500"}>
                {value.toString()}
              </Text>
            );
          }

          return <Text>{value.toString()}</Text>;
        },
      }),
    );

    return {
      columns: resultColumns,
      tableData: results as GraphQLResultRow[],
    };
  }, [objectsQuery.data]);

  // Create the table instance
  const table = useReactTable({
    data: tableData,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  const defaultQuery = `query {
  # Enter your GraphQL query here
  # Example:
  # users {
  #   id
  #   name
  #   email
  # }
}`;

  return (
    <VStack gap={6} align="stretch" p={6}>
      <VStack gap={4} align="stretch">
        <Text fontWeight="medium" fontSize="lg">
          GraphQL Query
        </Text>

        <Textarea
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyPress}
          placeholder={defaultQuery}
          rows={8}
          fontFamily="mono"
          fontSize="sm"
        />

        <HStack justify="space-between" align="center">
          <Text fontSize="sm" color="fg.muted">
            Press Ctrl+Enter to execute
          </Text>
          <Button
            onClick={handleSubmit}
            disabled={
              !query.trim() ||
              objectsQuery.isExecuting ||
              !objectsQuery.isReady
            }
            colorPalette="primary"
          >
            <Play size={16} />
            Run Query
          </Button>
        </HStack>
      </VStack>

      {/* Error Display */}
      {objectsQuery.error && (
        <Box>
          <Text fontWeight="medium" fontSize="lg" color="red.500" mb={2}>
            Query Error
          </Text>
          <Textarea
            value={`Error: ${objectsQuery.error.message || objectsQuery.error}`}
            readOnly
            rows={4}
            bg="red.50"
            borderColor="red.200"
            color="red.600"
            fontFamily="mono"
            fontSize="sm"
          />
        </Box>
      )}

      {/* GraphQL Errors Display */}
      {objectsQuery.data?.errors && objectsQuery.data.errors.length > 0 && (
        <Box>
          <Text fontWeight="medium" fontSize="lg" color="orange.500" mb={2}>
            GraphQL Errors
          </Text>
          <Textarea
            value={objectsQuery.data.errors
              .map(
                (error: Record<string, unknown>) =>
                  (error.message as string) || JSON.stringify(error),
              )
              .join("\n\n")}
            readOnly
            rows={6}
            bg="orange.50"
            borderColor="orange.200"
            color="orange.600"
            fontFamily="mono"
            fontSize="sm"
          />
        </Box>
      )}

      {/* Results Table */}
      {objectsQuery.data?.data && tableData.length > 0 && (
        <VStack gap={4} align="stretch">
          <HStack justify="space-between" align="center">
            <Text fontWeight="medium" fontSize="lg">
              Query Results
            </Text>
            <Text fontSize="sm" color="fg.muted">
              {tableData.length} row{tableData.length !== 1 ? "s" : ""}
            </Text>
          </HStack>

          <Box overflowX="auto">
            <BasicTable table={table} />
          </Box>
        </VStack>
      )}

      {/* No Results Message */}
      {objectsQuery.data?.data &&
        tableData.length === 0 &&
        !objectsQuery.error && (
          <Box>
            <Text fontWeight="medium" fontSize="lg" mb={2}>
              Query Results
            </Text>
            <Text color="fg.muted">
              Query executed successfully but returned no data.
            </Text>
          </Box>
        )}
    </VStack>
  );
};

export default RunGraphQLTab;
