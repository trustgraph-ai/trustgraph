import React from "react";
import {
  Box,
  Stack,
  Image,
  Flex,
  Heading,
  Text,
  Center,
} from "@chakra-ui/react";

const OptionWithImage: React.FC<{
  image: string;
  title: string;
  description?: string | React.ReactNode;
  badge?: React.ReactNode;
}> = ({ description, title, image, badge }) => {
  return (
    <Stack>
      <Flex alignItems="center">
        <Box mr={4} minWidth="5rem" width="5rem">
          <Center>
            <Image rounded="md" src={image} alt={title} />
          </Center>
        </Box>
        <Box>
          <Flex alignItems="center">
            <Heading as="h1" size="md" color="fg" fontWeight="bold" mr={2}>
              {title}
            </Heading>
            {badge && badge}
          </Flex>
          <Text mt={1} textStyle="xs" color="fg.muted">
            {description}
          </Text>
        </Box>
      </Flex>
    </Stack>
  );
};

export default OptionWithImage;
