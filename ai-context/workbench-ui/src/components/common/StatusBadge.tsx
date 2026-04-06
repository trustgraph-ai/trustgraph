import React from "react";
import { Badge, BadgeProps } from "@chakra-ui/react";
type StatusType = "success" | "warning" | "error" | "info" | "default";
interface StatusBadgeProps extends Omit<BadgeProps, "colorScheme"> {
  status: StatusType;
  label: string;
}
const StatusBadge: React.FC<StatusBadgeProps> = ({
  status,
  label,
  ...rest
}) => {
  const colorSchemes: Record<StatusType, string> = {
    success: "#65c97a",
    warning: "orange",
    error: "red",
    info: "#5285ed",
    default: "gray",
  };
  return (
    <Badge
      px={2}
      py={1}
      borderRadius="md"
      bg={colorSchemes[status]}
      color={status === "default" ? "gray.800" : "white"}
      fontWeight="medium"
      fontSize="xs"
      {...rest}
    >
      {label}
    </Badge>
  );
};
export default StatusBadge;
