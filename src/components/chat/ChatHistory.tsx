import React, { useEffect, useRef } from "react";

import { Box, Text, VStack, HStack, Avatar, Spacer } from "@chakra-ui/react";

import { useConversation } from "@trustgraph/react-state";
import ChatMessage from "./ChatMessage";
import ChatModeSelector from "./ChatModeSelector";

const ChatHistory = () => {
  const messages = useConversation((state) => state.messages);

  const scrollRef = useRef<HTMLInputElement>(null);

  const scrollToElement = () => {
    const { current } = scrollRef;
    if (current !== null) {
      current.scrollIntoView({ behavior: "smooth" });
    }
  };

  useEffect(scrollToElement, [messages]);

  return (
    <VStack
      spacing={4}
      align="stretch"
      borderWidth="1px"
      borderRadius="lg"
      overflowY="auto"
      maxH="calc(90% - 10rem)"
    >
      <Box bg="bg.emphasized" p={4} borderBottomWidth="1px">
        <HStack>
          <Avatar.Root size="sm" colorPalette="accent" mr={4}>
            <Avatar.Fallback name="Bot" />
          </Avatar.Root>
          <Text fontWeight="bold">Assistant</Text>
          <ChatModeSelector />
          <Spacer />
          <Text fontSize="sm" color="fg.muted">
            Online
          </Text>
        </HStack>
      </Box>

      <VStack
        flex={1}
        spacing={4}
        maxH="100%"
        overflowY="scroll"
        p={4}
        align="stretch"
      >
        {messages.map((message, ix) => (
          <ChatMessage key={ix} message={message} />
        ))}
        <div ref={scrollRef}></div>
      </VStack>
    </VStack>
  );
};

export default ChatHistory;
