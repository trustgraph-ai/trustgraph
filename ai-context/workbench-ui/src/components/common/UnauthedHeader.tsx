import { Box, Flex } from "@chakra-ui/react";

import ColorModeToggle from "../color-mode-toggle";

const UnauthedHeader = () => {
  return (
    <>
      <Flex
        mb={2}
        alignItems="center"
        justifyContent="space-between"
        width="100%"
        px={4}
        py={2}
      >
        <Flex mb={2} alignItems="center"></Flex>
        <Box>
          <ColorModeToggle />
        </Box>
      </Flex>
    </>
  );
};

export default UnauthedHeader;
