import React, { useState, useRef, useEffect, useMemo } from "react";

import { SendHorizontal } from "lucide-react";
import { useFlows } from "@trustgraph/react-state";

import {
  List,
  Portal,
  Button,
  Dialog,
  Box,
  CloseButton,
} from "@chakra-ui/react";

import SelectField from "../common/SelectField";
import SelectOption from "../common/SelectOption";
import ChipInputField from "../common/ChipInputField";

const SubmitDialog = ({ open, onOpenChange, onSubmit, docs }) => {
  const flowState = useFlows();
  const flows = useMemo(
    () => (flowState.flows ? flowState.flows : []),
    [flowState.flows],
  );

  const flowOptions = flows.map((flow) => {
    return {
      value: flow.id,
      label: flow.description,
      description: (
        <SelectOption title={flow.description}>
          {flow[0]} (class {flow["class-name"]})
        </SelectOption>
      ),
    };
  });

  const [flow, setFlow] = useState([]);
  const [tags, setTags] = useState([]);

  // Set default flow when flows are loaded or dialog opens
  useEffect(() => {
    if (open && flows.length > 0 && flow.length === 0) {
      setFlow([flows[0].id]);
    }
  }, [open, flows, flow]);

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
              <Dialog.Title>Submit documents for processing</Dialog.Title>
            </Dialog.Header>
            <Dialog.Body>
              <Box>Submit the following documents:</Box>

              <List.Root mt={5}>
                {docs.map((row) => (
                  <List.Item key={row.id} ml="1.5rem">
                    {row.title ? row.title : "<untitled>"}
                  </List.Item>
                ))}
              </List.Root>

              <Box mt={5}>With following flows:</Box>

              <Box mt={5}>
                <SelectField
                  label="Processing flow"
                  items={flowOptions}
                  value={flow}
                  onValueChange={(values) => {
                    setFlow(values);
                  }}
                  contentRef={contentRef}
                />
              </Box>

              <ChipInputField
                label="Tags"
                values={tags}
                onValuesChange={setTags}
              />
            </Dialog.Body>
            <Dialog.Footer>
              <Button variant="outline" onClick={() => onOpenChange(false)}>
                Cancel
              </Button>
              <Button
                onClick={() =>
                  onSubmit(flow.length > 0 ? flow[0] : null, tags)
                }
                colorPalette="primary"
              >
                <SendHorizontal /> Submit
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

export default SubmitDialog;
