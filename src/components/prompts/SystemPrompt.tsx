import { Code, Box } from "@chakra-ui/react";

const SystemPrompt = ({ prompt, onEdit }) => {
  return (
    <>
      <Box
        onClick={() => onEdit()}
        p={4}
        _hover={{ backgroundColor: "bg.emphasized" }}
      >
        <Code p={2}>{prompt}</Code>
      </Box>
    </>
  );
};

export default SystemPrompt;
