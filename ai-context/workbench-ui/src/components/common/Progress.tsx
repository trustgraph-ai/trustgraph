import React from "react";

import { Box, Text } from "@chakra-ui/react";

import { useProgressStateStore } from "@trustgraph/react-state";

const Progress: React.FC = () => {
  const activity = useProgressStateStore((state) => state.activity);

  return (
    <>
      {activity.size > 0 && (
        <Box
          position="absolute"
          bottom="1rem"
          left="1rem"
          zIndex="999"
          pt="0.8rem"
          pb="0.8rem"
          pl="1.2rem"
          pr="1.2rem"
          backgroundColor="bg.emphasized/40"
          borderWidth="1px"
          borderColor="border.inverted/40"
          borderRadius="5px"
          width="25rem"
        >
          {Array.from(activity)
            .slice(0, 4)
            .map((a, ix) => (
              <Box key={ix} color="fg/40" truncate>
                <Text textStyle="sm">{a}...</Text>
              </Box>
            ))}
        </Box>
      )}
    </>
  );
};

export default Progress;
