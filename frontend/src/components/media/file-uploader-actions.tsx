import { LoaderCircle, Plus, RotateCcw, Upload } from "lucide-react";

import { Button } from "@/components/ui/button";

interface FileUploaderActionsProps {
  canChoose: boolean;
  disabled: boolean;
  failedCount: number;
  isBusy: boolean;
  onChoose: () => void;
  onUpload: () => void;
  pendingCount: number;
}

export function FileUploaderActions({
  canChoose,
  disabled,
  failedCount,
  isBusy,
  onChoose,
  onUpload,
  pendingCount,
}: FileUploaderActionsProps) {
  const retryOnly = failedCount > 0 && failedCount === pendingCount;

  return (
    <div className="flex w-full flex-col-reverse gap-2 sm:w-auto sm:flex-row">
      {canChoose ? (
        <Button
          className="w-full sm:w-auto"
          disabled={disabled || isBusy}
          onClick={onChoose}
          type="button"
          variant="outline"
        >
          <Plus aria-hidden="true" className="size-4" />
          Thêm tệp
        </Button>
      ) : null}
      {pendingCount > 0 || isBusy ? (
        <Button
          aria-busy={isBusy}
          className="w-full sm:w-auto"
          disabled={disabled || isBusy}
          onClick={onUpload}
          type="button"
        >
          {isBusy ? (
            <LoaderCircle aria-hidden="true" className="size-4 animate-spin" />
          ) : retryOnly ? (
            <RotateCcw aria-hidden="true" className="size-4" />
          ) : (
            <Upload aria-hidden="true" className="size-4" />
          )}
          {isBusy
            ? "Đang xử lý"
            : retryOnly
              ? `Thử lại ${failedCount} tệp`
              : `Tải lên ${pendingCount} tệp`}
        </Button>
      ) : null}
    </div>
  );
}
