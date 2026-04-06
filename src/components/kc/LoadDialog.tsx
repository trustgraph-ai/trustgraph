import React, { useState, useRef } from "react";

import { Play } from "lucide-react";

import { Portal, Button, Dialog, Box, CloseButton } from "@chakra-ui/react";

import { useFlows } from "@trustgraph/react-state";
import SelectField from "../common/SelectField";
import SelectOption from "../common/SelectOption";

const LoadDialog = ({ open, onOpenChange, selectedIds, onLoad }) => {
  const flowState = useFlows();

  const flows = flowState.flows ? flowState.flows : [];

  const [selectedFlow, setSelectedFlow] = useState(undefined);

  const onSubmit = () => {
    if (!selectedFlow) return;

    onLoad(selectedIds, selectedFlow);
    onOpenChange(false);
  };

  const flowOptions = flows.map((flow) => {
    return {
      value: flow.id,
      label: flow.description || flow.id,
      description: (
        <SelectOption title={flow.description || flow.id}>
          {flow.id}
        </SelectOption>
      ),
    };
  });

  const contentRef = useRef<HTMLDivElement>(null);

  return (
    <Dialog.Root
      placement="center"
      open={open}
      onOpenChange={(x) => {
        onOpenChange(x.open);
      }}
    >
      <Portal>
        <Dialog.Backdrop />
        <Dialog.Positioner>
          <Dialog.Content ref={contentRef}>
            <Dialog.Header>
              <Dialog.Title>Load Knowledge Cores</Dialog.Title>
            </Dialog.Header>
            <Dialog.Body>
              <Box>
                Load {selectedIds.length} knowledge core(s) with the following
                flow:
              </Box>

              <Box mt={5}>
                <SelectField
                  label="Processing flow"
                  items={flowOptions}
                  value={selectedFlow}
                  onValueChange={(x) => {
                    setSelectedFlow(x);
                  }}
                  contentRef={contentRef}
                />
              </Box>
            </Dialog.Body>
            <Dialog.Footer>
              <Button variant="outline" onClick={() => onOpenChange(false)}>
                Cancel
              </Button>
              <Button
                onClick={() => onSubmit()}
                colorPalette="primary"
                disabled={!selectedFlow}
              >
                <Play /> Load
              </Button>
            </Dialog.Footer>
            <Dialog.CloseTrigger asChild>
              <CloseButton size="sm" />
            </Dialog.CloseTrigger>
          </Dialog.Content>
        </Dialog.Positioner>
      </Portal>
    </Dialog.Root>
  );
};

export default LoadDialog;
