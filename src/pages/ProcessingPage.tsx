import React from "react";
import { CircleArrowRight } from "lucide-react";

import PageHeader from "../components/common/PageHeader";
import Processing from "../components/processing/Processing";

const ProcessingPage = () => {
  return (
    <>
      <PageHeader
        icon={<CircleArrowRight />}
        title="Processing"
        description="Submit documents for processing"
      />
      <Processing />
    </>
  );
};

export default ProcessingPage;
