import React from "react";
import { useNavigate } from "react-router";
import { Rotate3d, ArrowBigRight } from "lucide-react";

import { Box, Alert, Button, Stack, Heading, HStack } from "@chakra-ui/react";

import {
  useWorkbenchStateStore,
  useSessionStore,
  useEntityDetail,
  useSettings,
} from "@trustgraph/react-state";

import EntityHelp from "./EntityHelp";
import ElementNode from "./ElementNode";

const EntityDetail = () => {
  const navigate = useNavigate();
  const flowId = useSessionStore((state) => state.flowId);
  const selected = useWorkbenchStateStore((state) => state.selected);
  const { settings, isLoaded: settingsLoaded } = useSettings();

  // Use the new Tanstack Query hook for entity details
  const { detail, isLoading, isError } = useEntityDetail(
    selected?.uri,
    flowId,
    settings?.collection || "default",
  );

  if (!settingsLoaded) {
    return (
      <Box>
        <Alert.Root status="info" variant="outline">
          <Alert.Indicator />
          <Alert.Title>Loading settings...</Alert.Title>
        </Alert.Root>
      </Box>
    );
  }

  if (!selected) {
    return (
      <Box>
        <Alert.Root severity="info" variant="outlined">
          <Alert.Indicator />
          <Alert.Title>
            No data to view. Try Chat or Search to find data.
          </Alert.Title>
        </Alert.Root>
      </Box>
    );
  }

  if (isLoading || !detail)
    return (
      <Box>
        <Alert.Root status="info" variant="outline">
          <Alert.Indicator />
          <Alert.Title>
            {isLoading
              ? "Loading entity details..."
              : "No data to view. Try Chat or Search to find data."}
          </Alert.Title>
        </Alert.Root>
      </Box>
    );

  if (isError)
    return (
      <Box>
        <Alert.Root status="error" variant="outline">
          <Alert.Indicator />
          <Alert.Title>Error loading entity details.</Alert.Title>
        </Alert.Root>
      </Box>
    );

  const graphView = () => {
    navigate("/graph");
  };

  return (
    <>
      <HStack mb={8}>
        <Heading>{selected.label}</Heading>

        <Box ml={8}>
          <Button size="md" variant="solid" onClick={() => graphView()}>
            <Rotate3d /> Graph view
          </Button>
        </Box>

        <EntityHelp />
      </HStack>

      <Box>
        {detail.triples.map((t) => {
          return (
            <Box key={t.s.v + "//" + t.p.v + "//" + t.o.v} mb={2}>
              <Stack direction="row" alignItems="center" gap={0}>
                <ElementNode value={t.s} selected={selected} />
                <ArrowBigRight />
                <ElementNode value={t.p} selected={selected} />
                <ArrowBigRight />
                <ElementNode value={t.o} selected={selected} />
              </Stack>
            </Box>
          );
        })}
      </Box>
    </>
  );
};

export default EntityDetail;
