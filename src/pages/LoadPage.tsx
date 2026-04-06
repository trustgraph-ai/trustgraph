import React from "react";
import { FileUp } from "lucide-react";

import { SimpleGrid, Stack, Box } from "@chakra-ui/react";

import { useSocket } from "@trustgraph/react-provider";

import Title from "../components/load/Title";
import Comments from "../components/load/Comments";
import Url from "../components/load/Url";
import Keywords from "../components/load/Keywords";
import Operation from "../components/load/Operation";
import Content from "../components/load/Content";
import { useProgressStateStore } from "@trustgraph/react-state";
import { useLoadStateStore } from "@trustgraph/react-state";
import PageHeader from "../components/common/PageHeader";
import { loadFile, loadText } from "../utils/document-load";
import { toaster } from "../components/ui/toaster";

const Load = () => {
  const title = useLoadStateStore((state) => state.title);
  const comments = useLoadStateStore((state) => state.comments);
  const url = useLoadStateStore((state) => state.url);
  const keywords = useLoadStateStore((state) => state.keywords);
  const operation = useLoadStateStore((state) => state.operation);
  const files = useLoadStateStore((state) => state.files);
  const text = useLoadStateStore((state) => state.text);
  const setText = useLoadStateStore((state) => state.setText);
  const addUploaded = useLoadStateStore((state) => state.addUploaded);
  const removeFile = useLoadStateStore((state) => state.removeFile);
  const incTextUploads = useLoadStateStore((state) => state.incTextUploads);

  const addActivity = useProgressStateStore((state) => state.addActivity);
  const removeActivity = useProgressStateStore(
    (state) => state.removeActivity,
  );

  const socket = useSocket();

  const onFilesSubmit = () => {
    const filesToLoad = [...files];

    // Shouldn't happen, make it a noop
    if (filesToLoad.length == 0) return;

    loadOneFile(filesToLoad)
      .then(() => {
        console.log("Success");
        toaster.create({
          title: "Files uploaded",
          type: "success",
        });
      })
      .catch((e) =>
        toaster.create({
          title: "Error: " + e.toString(),
          type: "error",
        }),
      );
  };

  const loadOneFile = (files) => {
    const kind = operation == "upload-pdf" ? "application/pdf" : "text/plain";

    const act = "Uploading: " + files[0].name;
    addActivity(act);

    // Create a promise for the first file in the list
    const prom = loadFile(files[0], kind, {
      title: title,
      url: url,
      keywords: keywords,
      comments: comments,
      socket: socket,
    })
      .then(() => {
        toaster.create({
          title: files[0].name + " uploaded",
          type: "info",
        });

        // Add file to 'uploaded' list
        addUploaded(files[0].name);
        removeFile(files[0]);

        removeActivity(act);
      })
      .catch((e) => {
        removeActivity(act);
        throw e;
      });

    if (files.length < 2) {
      return prom;
    } else {
      return prom.then(() => loadOneFile(files.slice(1)));
    }
  };

  const onTextSubmit = () => {
    loadText(text, {
      title: title,
      url: url,
      keywords: keywords,
      comments: comments,
      addActivity: addActivity,
      removeActivity: removeActivity,
      onSuccess: () => handleTextSuccess(),
      socket: socket,
    })
      .then(() => {
        setText("");
        incTextUploads();
        toaster.create({
          title: "Text uploaded",
          type: "success",
        });
      })
      .catch((e) =>
        toaster.create({
          title: "Error: " + e.toString(),
          type: "error",
        }),
      );
  };

  return (
    <>
      <PageHeader
        icon={<FileUp />}
        title="Document load"
        description="Load documents into TrustGraph processing"
      />

      <SimpleGrid minChildWidth="sm" gap={8}>
        <Stack>
          <Title />
          <Url />
          <Keywords />
        </Stack>
        <Box>
          <Comments />
          <Operation />
        </Box>
      </SimpleGrid>
      <Content
        submitFiles={() => onFilesSubmit()}
        submitText={() => onTextSubmit()}
      />
    </>
  );
};

export default Load;
