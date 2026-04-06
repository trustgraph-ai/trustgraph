import { useState } from "react";

import { Text, Box, Stack, HStack, Popover, Portal } from "@chakra-ui/react";

import { Database, Workflow } from "lucide-react";

import { useSessionStore } from "@trustgraph/react-state";
import { useFlows } from "@trustgraph/react-state";
import { useSettings } from "@trustgraph/react-state";
import { useCollections } from "@trustgraph/react-state";

const FlowSelector = () => {
  const flowState = useFlows();
  const flows = flowState.flows ? flowState.flows : [];

  const collectionsState = useCollections();
  const collections = collectionsState.collections || [];

  const flowId = useSessionStore((state) => state.flowId);

  const setFlowId = useSessionStore((state) => state.setFlowId);
  const setFlow = useSessionStore((state) => state.setFlow);

  const { settings, updateSetting } = useSettings();

  const [open, setOpen] = useState(false);

  return (
    <Popover.Root
      open={open}
      onOpenChange={(e) => setOpen(e.open)}
      size="xl"
      positioning={{ placement: "bottom-end" }}
    >
      <Popover.Trigger asChild>
        <Stack
          p={3}
          gap={2}
          borderWidth="1px"
          borderRadius="8px"
          borderColor="border.inverted/20"
          color="fg.muted"
          backgroundColor="primary.bg"
          _hover={{
            backgroundColor: "bg.emphasized",
            borderColor: "border.inverted",
            color: "fg",
          }}
          onClick={() => setOpen(true)}
          cursor="pointer"
        >
          <HStack gap={2} align="center">
            <Database size={14} />
            <Text fontSize="xs" fontWeight="medium">
              {settings.collection}
            </Text>
          </HStack>

          <HStack gap={2} align="center">
            <Workflow size={14} />
            <Text fontSize="xs" fontWeight="medium">
              {flowId || "<none>"}
            </Text>
          </HStack>
        </Stack>
      </Popover.Trigger>
      <Portal>
        <Popover.Positioner>
          <Popover.Content>
            <Popover.Arrow />
            <Popover.Body>
              <Stack gap={4} p={4}>
                {/* Collection Selection */}
                <Stack gap={3}>
                  <Text
                    fontSize="sm"
                    fontWeight="semibold"
                    color="fg.muted"
                    mb={2}
                  >
                    Select Collection
                  </Text>
                  <Stack gap="1">
                    {collections.map((collection) => {
                      const isSelected =
                        settings.collection === collection.collection;
                      return (
                        <Box
                          key={collection.collection}
                          p={3}
                          borderRadius="md"
                          borderWidth="1px"
                          borderColor={
                            isSelected ? "primary.500" : "border.subtle"
                          }
                          backgroundColor={
                            isSelected ? "primary.50" : "transparent"
                          }
                          _hover={{
                            borderColor: "primary.300",
                            backgroundColor: isSelected
                              ? "primary.100"
                              : "bg.subtle",
                          }}
                          cursor="pointer"
                          onClick={() => {
                            updateSetting("collection", collection.collection);
                          }}
                        >
                          <HStack gap={3} align="start">
                            <Box
                              w={4}
                              h={4}
                              borderRadius="full"
                              borderWidth="2px"
                              borderColor={
                                isSelected
                                  ? "colorPalette.500"
                                  : "border.emphasized"
                              }
                              backgroundColor={
                                isSelected ? "colorPalette.500" : "transparent"
                              }
                              mt={0.5}
                              flexShrink={0}
                              position="relative"
                            >
                              {isSelected && (
                                <Box
                                  w="6px"
                                  h="6px"
                                  borderRadius="full"
                                  backgroundColor="bg"
                                  position="absolute"
                                  top="50%"
                                  left="50%"
                                  transform="translate(-50%, -50%)"
                                />
                              )}
                            </Box>
                            <Box flex="1">
                              <Text fontWeight="semibold" fontSize="sm" mb={1}>
                                {collection.name}
                              </Text>
                              <Text
                                fontSize="xs"
                                color="fg.muted"
                                lineHeight="1.4"
                              >
                                {collection.description}
                              </Text>
                            </Box>
                          </HStack>
                        </Box>
                      );
                    })}
                  </Stack>
                </Stack>

                {/* Flow Selection */}
                <Box borderTopWidth="1px" borderColor="border.subtle" pt={4}>
                  <Text
                    fontSize="sm"
                    fontWeight="semibold"
                    color="fg.muted"
                    mb={3}
                  >
                    Select Flow
                  </Text>
                  <Stack gap="1">
                    {flows.map((flow) => {
                      const isSelected = flowId === flow.id;
                      return (
                        <Box
                          key={flow.id}
                          p={3}
                          borderRadius="md"
                          borderWidth="1px"
                          borderColor={
                            isSelected ? "primary.500" : "border.subtle"
                          }
                          backgroundColor={
                            isSelected ? "primary.50" : "transparent"
                          }
                          _hover={{
                            borderColor: "primary.300",
                            backgroundColor: isSelected
                              ? "primary.100"
                              : "bg.subtle",
                          }}
                          cursor="pointer"
                          onClick={() => {
                            setFlowId(flow.id);
                            setFlow(flow);
                          }}
                        >
                          <HStack gap={3} align="start">
                            <Box
                              w={4}
                              h={4}
                              borderRadius="full"
                              borderWidth="2px"
                              borderColor={
                                isSelected
                                  ? "colorPalette.500"
                                  : "border.emphasized"
                              }
                              backgroundColor={
                                isSelected ? "colorPalette.500" : "transparent"
                              }
                              mt={0.5}
                              flexShrink={0}
                              position="relative"
                            >
                              {isSelected && (
                                <Box
                                  w="6px"
                                  h="6px"
                                  borderRadius="full"
                                  backgroundColor="bg"
                                  position="absolute"
                                  top="50%"
                                  left="50%"
                                  transform="translate(-50%, -50%)"
                                />
                              )}
                            </Box>
                            <Box flex="1">
                              <Text fontWeight="semibold" fontSize="sm" mb={1}>
                                {flow.id}
                              </Text>
                              <Text
                                fontSize="xs"
                                color="fg.muted"
                                lineHeight="1.4"
                              >
                                {flow.description}
                              </Text>
                            </Box>
                          </HStack>
                        </Box>
                      );
                    })}
                  </Stack>
                </Box>
              </Stack>
            </Popover.Body>
          </Popover.Content>
        </Popover.Positioner>
      </Portal>
    </Popover.Root>
  );
};

export default FlowSelector;
