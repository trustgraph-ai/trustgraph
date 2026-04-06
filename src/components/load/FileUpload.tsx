import React, { useRef } from "react";

import { Button, Box } from "@chakra-ui/react";

import { FilePlus } from "lucide-react";

import SelectedFiles from "./SelectedFiles";
import { useLoadStateStore } from "@trustgraph/react-state";

interface FileUploadProps {
  kind: string;
}

const FileUpload: React.FC<FileUploadProps> = ({ kind }) => {
  const setFiles = useLoadStateStore((state) => state.setFiles);

  const fl2a = (x: FileList | null): File[] => {
    if (x) return Array.from(x);
    else return [];
  };

  const fileInput = useRef(null);

  return (
    <>
      <Box>
        <Button
          mt={5}
          mb={5}
          component="label"
          variant="solid"
          colorPalette="primary"
          onClick={() => fileInput.current.click()}
        >
          <FilePlus /> Select {kind} files
        </Button>

        <input
          ref={fileInput}
          type="file"
          onChange={(event) => setFiles(fl2a(event.target.files))}
          style={{
            clip: "rect(0 0 0 0)",
            clipPath: "inset(50%)",
            overflow: "hidden",
            position: "absolute",
            bottom: 0,
            left: 0,
            whitespace: "nowrap",
            width: 1,
          }}
          multiple
        />
      </Box>

      <Box>
        <SelectedFiles />
      </Box>
    </>
  );
};

export default FileUpload;
