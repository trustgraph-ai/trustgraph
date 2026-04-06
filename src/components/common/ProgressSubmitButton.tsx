import React from "react";

import { SendHorizontal } from "lucide-react";

import { Box, Button } from "@chakra-ui/react";

interface ProgressSubmitButtonProps {
  disabled: boolean;
  working: boolean;
  onClick: () => void;
}

const ProgressSubmitButton: React.FC<ProgressSubmitButtonProps> = ({
  disabled,
  working,
  onClick,
}) => {
  return (
    <Box>
      <Button
        variant="subtle"
        disabled={disabled}
        loading={working}
        color="primary"
        onClick={() => onClick()}
      >
        Send <SendHorizontal />
      </Button>
    </Box>
  );
};

export default ProgressSubmitButton;
