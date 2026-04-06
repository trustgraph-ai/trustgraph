import React, { useRef } from "react";

import { Input, HStack } from "@chakra-ui/react";

import {
  useProgressStateStore,
  useConversation,
} from "@trustgraph/react-state";
import ChatHelp from "./ChatHelp";
import ProgressSubmitButton from "../common/ProgressSubmitButton";

interface InputAreaProps {
  onSubmit: () => void;
}

const InputArea: React.FC<InputAreaProps> = ({ onSubmit }) => {
  const input = useConversation((state) => state.input);
  const setInput = useConversation((state) => state.setInput);
  const activity = useProgressStateStore((state) => state.activity);

  const inputRef = useRef<HTMLInputElement>(null);

  const submit = () => {
    onSubmit();
    if (inputRef.current) {
      inputRef.current.focus();
    }
  };

  const onKeyDown = (event) => {
    if (event.key == "Enter") {
      onSubmit();
    }
  };

  return (
    <>
      <HStack mt={4}>
        <Input
          w="full"
          variant="outlined"
          placeholder="Describe a Graph RAG request..."
          value={input}
          ref={inputRef}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={onKeyDown}
        />

        <ProgressSubmitButton
          disabled={activity.size > 0}
          working={activity.size > 0}
          onClick={() => submit()}
        />

        <ChatHelp />
      </HStack>
    </>
  );
};

export default InputArea;
