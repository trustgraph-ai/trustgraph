import React from "react";
import { Settings } from "lucide-react";
import PageHeader from "../components/common/PageHeader";
import SettingsComponent from "../components/settings/Settings";

const SettingsPage: React.FC = () => {
  return (
    <>
      <PageHeader
        icon={<Settings />}
        title="Settings"
        description="Configure application preferences and system settings"
      />
      <SettingsComponent />
    </>
  );
};

export default SettingsPage;
