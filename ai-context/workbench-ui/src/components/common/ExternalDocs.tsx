import React, { PropsWithChildren } from "react";

import { Link } from "@chakra-ui/react";

const ExternalDocs: React.FC<
  PropsWithChildren<{
    href: string;
  }>
> = ({ href, children }) => {
  return (
    <Link href={href} target="_blank" colorPalette="accent">
      {children}
    </Link>
  );
};

export default ExternalDocs;
