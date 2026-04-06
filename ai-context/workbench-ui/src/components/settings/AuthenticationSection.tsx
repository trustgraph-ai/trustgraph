import React, { useState, useEffect } from "react";
import { VStack, HStack, IconButton, Text, Button } from "@chakra-ui/react";
import { Eye, EyeOff, Key, Save, RotateCcw } from "lucide-react";
import Card from "../common/Card";
import TextField from "../common/TextField";

interface AuthenticationSectionProps {
  apiKey: string;
  onApiKeyChange: (value: string) => void;
  isSaving?: boolean;
}

const AuthenticationSection: React.FC<AuthenticationSectionProps> = ({
  apiKey,
  onApiKeyChange,
  isSaving = false,
}) => {
  const [showApiKey, setShowApiKey] = useState(false);
  const [stagedApiKey, setStagedApiKey] = useState(apiKey);

  // Keep staged value in sync with saved value
  useEffect(() => {
    setStagedApiKey(apiKey);
  }, [apiKey]);

  const toggleApiKeyVisibility = () => {
    setShowApiKey(!showApiKey);
  };

  const handleSave = () => {
    onApiKeyChange(stagedApiKey);
  };

  const handleReset = () => {
    setStagedApiKey(apiKey);
  };

  const hasChanges = stagedApiKey !== apiKey;

  return (
    <Card
      title="Authentication"
      description="Configure API authentication for TrustGraph socket connections"
      icon={<Key />}
    >
      <VStack gap={4} align="stretch">
        <VStack gap={2} align="stretch">
          <HStack justify="space-between">
            <Text fontWeight="medium">API Key</Text>
            <IconButton
              size="sm"
              variant="ghost"
              onClick={toggleApiKeyVisibility}
              aria-label={showApiKey ? "Hide API key" : "Show API key"}
            >
              {showApiKey ? <EyeOff /> : <Eye />}
            </IconButton>
          </HStack>
          <TextField
            placeholder="Enter API key (leave empty for no authentication)"
            value={stagedApiKey}
            onValueChange={setStagedApiKey}
            type={showApiKey ? "text" : "password"}
          />

          {hasChanges && (
            <HStack gap={2} justify="flex-end">
              <Button
                size="sm"
                variant="outline"
                onClick={handleReset}
                disabled={isSaving}
              >
                <RotateCcw />
                Reset
              </Button>
              <Button
                size="sm"
                colorPalette="primary"
                onClick={handleSave}
                disabled={isSaving}
                loading={isSaving}
              >
                <Save />
                Apply Key
              </Button>
            </HStack>
          )}

          <Text fontSize="sm" color={hasChanges ? "accent.fg" : "fg.muted"}>
            {hasChanges
              ? "API key changes require applying to reconnect websocket"
              : apiKey
                ? "API key active - socket authentication enabled"
                : "No API key set - authentication disabled"}
          </Text>
        </VStack>
      </VStack>
    </Card>
  );
};

export default AuthenticationSection;
