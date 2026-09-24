import { RoleGate } from "@/components/auth/role-gate";
import { TaskWorkspace } from "@/components/tasks/task-workspace";

export default function TasksPage() {
  return (
    <RoleGate allowed={["SUPER_ADMIN"]} permissions={["work.tasks.read"]}>
      <TaskWorkspace />
    </RoleGate>
  );
}
