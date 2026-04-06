import React, { useState, useMemo } from "react";
import { VStack, HStack, Button, Text, Box, Textarea } from "@chakra-ui/react";
import { Search } from "lucide-react";
import { useStructuredQuery } from "@trustgraph/react-state";
import TextField from "../common/TextField";
import {
  createColumnHelper,
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
} from "@tanstack/react-table";
import BasicTable from "../common/BasicTable";

// Dynamic table row type for structured query results
type StructuredQueryResultRow = Record<string, unknown>;

const columnHelper = createColumnHelper<StructuredQueryResultRow>();

const StructuredQueryTab: React.FC = () => {
  const [question, setQuestion] = useState("");
  const structuredQuery = useStructuredQuery();

  const handleSubmit = () => {
    if (!question.trim()) return;

    structuredQuery.executeQuery({ question: question.trim() });
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  // Dynamically create columns based on the first row of results
  const { columns, tableData } = useMemo(() => {
    if (!structuredQuery.queryData) {
      return { columns: [], tableData: [] };
    }

    // Extract the first array of results from the response
    // Structured query responses typically have structure like { data: { users: [...] } }
    const dataKeys = Object.keys(structuredQuery.queryData);
    if (dataKeys.length === 0) {
      return { columns: [], tableData: [] };
    }

    // Get the first data collection
    const firstKey = dataKeys[0];
    const results = structuredQuery.queryData[firstKey];

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
      tableData: results as StructuredQueryResultRow[],
    };
  }, [structuredQuery.queryData]);

  // Create the table instance
  const table = useReactTable({
    data: tableData,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  return (
    <VStack gap={6} align="stretch" p={6}>
      <VStack gap={4} align="stretch">
        <Text fontWeight="medium" fontSize="lg">
          Natural Language Question
        </Text>
        <TextField
          label="Question"
          value={question}
          onValueChange={setQuestion}
          placeholder="e.g., What are the top 5 products by sales this month?"
          onKeyDown={handleKeyPress}
        />
        <HStack justify="flex-end">
          <Button
            onClick={handleSubmit}
            disabled={
              !question.trim() ||
              structuredQuery.isExecuting ||
              !structuredQuery.isReady
            }
            colorPalette="primary"
          >
            <Search size={16} />
            Execute Query
          </Button>
        </HStack>
      </VStack>

      {/* Error Display */}
      {structuredQuery.error && (
        <Box>
          <Text fontWeight="medium" fontSize="lg" color="red.500" mb={2}>
            Query Error
          </Text>
          <Textarea
            value={`Error: ${structuredQuery.error.message || structuredQuery.error}`}
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

      {/* Query Errors Display */}
      {structuredQuery.queryErrors &&
        structuredQuery.queryErrors.length > 0 && (
          <Box>
            <Text fontWeight="medium" fontSize="lg" color="orange.500" mb={2}>
              Query Errors
            </Text>
            <Textarea
              value={structuredQuery.queryErrors
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
      {structuredQuery.queryData && tableData.length > 0 && (
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
      {structuredQuery.queryData &&
        tableData.length === 0 &&
        !structuredQuery.error && (
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

export default StructuredQueryTab;
