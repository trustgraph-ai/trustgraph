import { Box, SegmentGroup, Field, HStack } from "@chakra-ui/react";

import { useLoadStateStore } from "@trustgraph/react-state";

import LoadHelp from "./LoadHelp";

const Operation = () => {
  const value = useLoadStateStore((state) => state.operation);
  const setValue = useLoadStateStore((state) => state.setOperation);

  return (
    <>
      <Box>
        <HStack>
          <Field.Root>
            <Field.Label>Upload operation</Field.Label>
            <SegmentGroup.Root
              value={value}
              onValueChange={(v) => setValue(v.value)}
            >
              <SegmentGroup.Indicator />
              <SegmentGroup.Item key="upload-pdf" value="upload-pdf">
                <SegmentGroup.ItemText>PDF</SegmentGroup.ItemText>
                <SegmentGroup.ItemHiddenInput />
              </SegmentGroup.Item>
              <SegmentGroup.Item key="upload-text" value="upload-text">
                <SegmentGroup.ItemText>Text</SegmentGroup.ItemText>
                <SegmentGroup.ItemHiddenInput />
              </SegmentGroup.Item>
              <SegmentGroup.Item key="paste-text" value="paste-text">
                <SegmentGroup.ItemText>Paste</SegmentGroup.ItemText>
                <SegmentGroup.ItemHiddenInput />
              </SegmentGroup.Item>
            </SegmentGroup.Root>
            <Field.HelperText>
              Select one of the available upload operations
            </Field.HelperText>
          </Field.Root>
          <LoadHelp />
        </HStack>
      </Box>
    </>
  );
};

export default Operation;
