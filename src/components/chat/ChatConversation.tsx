import React from "react";

import ChatHistory from "./ChatHistory";
import InputArea from "./InputArea";
import EntityList from "../common/EntityList";

import { useConversation, useChat } from "@trustgraph/react-state";

const ChatConversation = () => {
  const input = useConversation((state) => state.input);
  const { submitMessage } = useChat();

  const submit = () => {
    if (input.trim()) {
      submitMessage({ input });
    }
  };

  return (
    <>
      <ChatHistory />
      <InputArea onSubmit={() => submit()} />
      <EntityList />
    </>
  );
};

export default ChatConversation;
