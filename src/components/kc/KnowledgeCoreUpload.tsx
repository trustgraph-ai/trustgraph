import React, { useRef } from "react";

import { Button, Box } from "@chakra-ui/react";

import { Upload, FilePlus } from "lucide-react";

import IdField from "./IdField";

interface KnowledgeCoreUploadProps {
  files;
  setFiles;
  id;
  setId;
  submit: () => void;
}

const KnowledgeCoreUpload: React.FC<KnowledgeCoreUploadProps> = ({
  submit,
  files,
  setFiles,
  id,
  setId,
}) => {
  const fl2a = (x: FileList | null): File[] => {
    if (x) return Array.from(x);
    else return [];
  };

  const fileInput = useRef(null);

  return (
    <>
      <Box mt={10}>
        <IdField value={id} setValue={setId} />
      </Box>

      <Box>
        <Button
          mt={5}
          mb={5}
          component="label"
          variant="solid"
          colorPalette="primary"
          onClick={() => fileInput.current.click()}
        >
          <FilePlus /> Select files
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
        />

        <Button
          mt={5}
          ml={5}
          mb={5}
          variant="solid"
          colorPalette="primary"
          onClick={() => submit()}
          disabled={files.length < 1}
        >
          <Upload /> Load
        </Button>
      </Box>

      <Box>
        {files.map((f, ix) => (
          <Box key={ix}>Selected: {f.name}</Box>
        ))}
      </Box>
    </>
  );
};

export default KnowledgeCoreUpload;
