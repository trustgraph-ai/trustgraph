import React, { useState, useEffect } from "react";
import { VStack, HStack, Text, Button } from "@chakra-ui/react";
import { User, Save, RotateCcw } from "lucide-react";
import Card from "../common/Card";
import TextField from "../common/TextField";

interface UserSectionProps {
  user: string;
  onUserChange: (value: string) => void;
  isSaving?: boolean;
}

const UserSection: React.FC<UserSectionProps> = ({
  user,
  onUserChange,
  isSaving = false,
}) => {
  const [stagedUser, setStagedUser] = useState(user);

  // Keep staged value in sync with saved value
  useEffect(() => {
    setStagedUser(user);
  }, [user]);

  const handleSave = () => {
    onUserChange(stagedUser.trim());
  };

  const handleReset = () => {
    setStagedUser(user);
  };

  const hasChanges = stagedUser.trim() !== user;
  const isValid = stagedUser.trim().length > 0;

  return (
    <Card
      title="User Identity"
      description="Configure the user ID for API requests and data operations"
      icon={<User />}
    >
      <VStack gap={4} align="stretch">
        <VStack gap={2} align="stretch">
          <Text fontWeight="medium">User ID</Text>
          <TextField
            placeholder="Enter user ID"
            value={stagedUser}
            onValueChange={setStagedUser}
            required
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
                disabled={isSaving || !isValid}
                loading={isSaving}
              >
                <Save />
                Apply User ID
              </Button>
            </HStack>
          )}

          <Text fontSize="sm" color={hasChanges ? "accent.fg" : "fg.muted"}>
            {hasChanges
              ? "User ID changes will apply to new API requests"
              : `Current user ID: ${user}`}
          </Text>
        </VStack>
      </VStack>
    </Card>
  );
};

export default UserSection;
