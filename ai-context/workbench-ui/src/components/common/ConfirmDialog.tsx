import React from "react";
import { Box, VStack, HStack, Text, Button } from "@chakra-ui/react";
import { AlertTriangle, X } from "lucide-react";

interface ConfirmDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  variant?: "danger" | "warning" | "info";
}

export const ConfirmDialog: React.FC<ConfirmDialogProps> = ({
  isOpen,
  onClose,
  onConfirm,
  title,
  message,
  confirmText = "Confirm",
  cancelText = "Cancel",
  variant = "warning",
}) => {
  if (!isOpen) return null;

  const handleConfirm = () => {
    onConfirm();
    onClose();
  };

  const getVariantColors = () => {
    switch (variant) {
      case "danger":
        return {
          icon: "red.500",
          confirmButton: "red",
          bg: "red.50",
          border: "red.200",
        };
      case "warning":
        return {
          icon: "orange.500",
          confirmButton: "orange",
          bg: "orange.50",
          border: "orange.200",
        };
      case "info":
        return {
          icon: "blue.500",
          confirmButton: "blue",
          bg: "blue.50",
          border: "blue.200",
        };
      default:
        return {
          icon: "orange.500",
          confirmButton: "orange",
          bg: "orange.50",
          border: "orange.200",
        };
    }
  };

  const colors = getVariantColors();

  return (
    <Box
      position="fixed"
      top="0"
      left="0"
      right="0"
      bottom="0"
      bg="blackAlpha.600"
      display="flex"
      alignItems="center"
      justifyContent="center"
      zIndex="modal"
    >
      <Box
        bg="white"
        borderRadius="lg"
        boxShadow="xl"
        w="500px"
        maxW="90vw"
        maxH="90vh"
        overflow="auto"
      >
        {/* Header */}
        <Box p={6} borderBottomWidth="1px">
          <HStack justify="space-between" align="center">
            <HStack>
              <AlertTriangle size={20} color={colors.icon} />
              <Text fontSize="lg" fontWeight="semibold">
                {title}
              </Text>
            </HStack>
            <Button variant="ghost" size="sm" onClick={onClose}>
              <X size={16} />
            </Button>
          </HStack>
        </Box>

        {/* Content */}
        <Box p={6}>
          <VStack align="stretch" spacing={4}>
            <Box
              p={4}
              bg={colors.bg}
              borderRadius="md"
              borderWidth="1px"
              borderColor={colors.border}
            >
              <Text fontSize="sm" color="gray.700" whiteSpace="pre-line">
                {message}
              </Text>
            </Box>
          </VStack>
        </Box>

        {/* Footer */}
        <Box p={6} borderTopWidth="1px" bg="gray.50">
          <HStack justify="flex-end" spacing={3}>
            <Button variant="ghost" onClick={onClose}>
              {cancelText}
            </Button>
            <Button
              colorPalette={colors.confirmButton}
              onClick={handleConfirm}
            >
              {confirmText}
            </Button>
          </HStack>
        </Box>
      </Box>
    </Box>
  );
};
