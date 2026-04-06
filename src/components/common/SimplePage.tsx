import React, { PropsWithChildren } from "react";

import { Box, Container, Flex, Heading, Stack } from "@chakra-ui/react";

import UnauthedHeader from "./UnauthedHeader";

const SimplePage: React.FC<
  PropsWithChildren<{
    title: string;
  }>
> = ({ title, children }) => {
  return (
    <>
      <UnauthedHeader />
      <Flex minH="100vh" align="center" justify="center" bg="primary.900">
        <Container maxW="md" py={12}>
          <Box
            bg="primary.800"
            p={8}
            borderRadius="md"
            boxShadow="lg"
            borderWidth="1px"
            borderColor="primary.muted"
          >
            <Stack spacing={6}>
              <Heading
                as="h1"
                fontSize="2xl"
                textAlign="center"
                color="primary.400"
                mb={2}
              >
                {title}
              </Heading>

              {children}
            </Stack>
          </Box>
        </Container>
      </Flex>
    </>
  );
};

export default SimplePage;
