/*
 * CRITICAL: DO NOT MODIFY THIS COMPONENT WITHOUT DESIGN AUTHORITY APPROVAL
 *
 * This SelectOptionText component is used by SelectField throughout the application.
 * Changes to this component's interface or styling will affect all dropdown
 * options across multiple domains. Any modifications require extensive testing
 * and approval from the application design authority.
 */

import React from "react";
import { Text } from "@chakra-ui/react";

const SelectOptionText: React.FC<{
  children: React.ReactNode;
}> = ({ children }) => {
  return (
    <Text mt={1} textStyle="xs" color="fg.muted">
      {children}
    </Text>
  );
};

export default SelectOptionText;
