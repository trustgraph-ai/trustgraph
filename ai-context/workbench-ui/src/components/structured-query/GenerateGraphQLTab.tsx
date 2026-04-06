import React, { useState } from "react";
import { VStack, HStack, Button, Textarea, Text } from "@chakra-ui/react";
import { ArrowRight } from "lucide-react";
import { useNlpQuery } from "@trustgraph/react-state";
import TextField from "../common/TextField";

const GenerateGraphQLTab: React.FC = () => {
  const [question, setQuestion] = useState("");
  const nlpQuery = useNlpQuery();

  const handleSubmit = () => {
    if (!question.trim()) return;

    nlpQuery.convertQuery({ question: question.trim() });
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

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
          placeholder="e.g., Show me all users created last month with their emails..."
          onKeyDown={handleKeyPress}
        />
        <HStack justify="flex-end">
          <Button
            onClick={handleSubmit}
            disabled={
              !question.trim() || nlpQuery.isConverting || !nlpQuery.isReady
            }
            colorPalette="primary"
          >
            <ArrowRight size={16} />
            Generate GraphQL
          </Button>
        </HStack>
      </VStack>

      {(nlpQuery.graphqlQuery || nlpQuery.error) && (
        <VStack gap={4} align="stretch">
          <Text fontWeight="medium" fontSize="lg">
            Generated GraphQL Query
          </Text>

          {nlpQuery.error ? (
            <Textarea
              value={`Error: ${nlpQuery.error.message || nlpQuery.error}`}
              readOnly
              rows={6}
              bg="bg.muted"
              color="red.500"
              fontFamily="mono"
            />
          ) : (
            <Textarea
              value={nlpQuery.graphqlQuery || ""}
              readOnly
              rows={12}
              bg="bg.muted"
              fontFamily="mono"
              fontSize="sm"
              placeholder="Generated GraphQL query will appear here..."
            />
          )}

          {nlpQuery.confidence !== undefined && (
            <Text fontSize="sm" color="fg.muted">
              Confidence: {Math.round(nlpQuery.confidence * 100)}%
            </Text>
          )}

          {nlpQuery.detectedSchemas && nlpQuery.detectedSchemas.length > 0 && (
            <VStack gap={2} align="start">
              <Text fontSize="sm" fontWeight="medium" color="fg.muted">
                Detected Schemas:
              </Text>
              <Text fontSize="sm" color="fg.muted">
                {nlpQuery.detectedSchemas
                  .map((schema: Record<string, unknown> | string) =>
                    typeof schema === "string"
                      ? schema
                      : (schema as Record<string, unknown>).name ||
                        JSON.stringify(schema),
                  )
                  .join(", ")}
              </Text>
            </VStack>
          )}

          {nlpQuery.variables &&
            Object.keys(nlpQuery.variables).length > 0 && (
              <VStack gap={2} align="start">
                <Text fontSize="sm" fontWeight="medium" color="fg.muted">
                  Variables:
                </Text>
                <Textarea
                  value={JSON.stringify(nlpQuery.variables, null, 2)}
                  readOnly
                  rows={4}
                  bg="bg.subtle"
                  fontFamily="mono"
                  fontSize="sm"
                />
              </VStack>
            )}
        </VStack>
      )}
    </VStack>
  );
};

export default GenerateGraphQLTab;
