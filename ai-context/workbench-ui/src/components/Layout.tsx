import React from "react";
import { Box, Flex } from "@chakra-ui/react";
import Sidebar from "./Sidebar";

interface LayoutProps {
  children: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  return (
    <Flex width="100%" minHeight="100vh">
      <Sidebar />
      <Box flex="1" p={6} overflowY="auto" maxHeight="100vh">
        {children}
      </Box>
    </Flex>
  );
};

export default Layout;
