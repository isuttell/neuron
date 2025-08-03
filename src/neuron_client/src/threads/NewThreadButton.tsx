import React from "react";
import { ListPlus } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { SidebarGroupAction } from "../components/ui/sidebar";

const NewThreadButton: React.FC = () => {
  const navigate = useNavigate();

  return (
    <SidebarGroupAction
      className="size-6"
      onClick={() => {
        navigate("/");
      }}
    >
      <ListPlus className="h-4 w-4" />
    </SidebarGroupAction>
  );
};

export default NewThreadButton;
