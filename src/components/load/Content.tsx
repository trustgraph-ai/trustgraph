import React from "react";

import TextBuffer from "./TextBuffer";
import FileUpload from "./FileUpload";
import { useLoadStateStore } from "@trustgraph/react-state";

const Content = () => {
  const operation = useLoadStateStore((state) => state.operation);

  if (operation == "upload-pdf") {
    return <FileUpload kind="PDF" />;
  }

  if (operation == "upload-text") {
    return <FileUpload kind="text" />;
  }

  return <TextBuffer />;
};

export default Content;
