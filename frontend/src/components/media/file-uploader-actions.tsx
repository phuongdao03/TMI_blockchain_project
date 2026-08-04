import { LoaderCircle, RotateCcw, UploadCloud } from "lucide-react";

import type { UploadStatus } from "@/components/media/use-media-uploader";
import { Button } from "@/components/ui/button";

interface FileUploaderActionsProps {
  disabled: boolean;
  hasFile: boolean;
  isBusy: boolean;
  onChoose: () => void;
  onUpload: () => void;
  status: UploadStatus;
}

export function FileUploaderActions({
  disabled,
  hasFile,
  isBusy,
  onChoose,
  onUpload,
  status,
}: FileUploaderActionsProps) {
  if (!hasFile || status === "complete") {
    return (
      <Button
        disabled={disabled || isBusy}
        onClick={onChoose}
        type="button"
        variant="outline"
      >
        Chọn tệp
      </Button>
    );
  }
  if (status === "selected") {
    return (
      <Button disabled={disabled} onClick={onUpload} type="button">
        <UploadCloud aria-hidden="true" className="size-4" />
        Tải lên
      </Button>
    );
  }
  if (status === "failed") {
    return (
      <Button disabled={disabled} onClick={onUpload} type="button">
        <RotateCcw aria-hidden="true" className="size-4" />
        Thử lại
      </Button>
    );
  }
  if (isBusy) {
    return (
      <Button disabled type="button">
        <LoaderCircle aria-hidden="true" className="size-4 animate-spin" />
        Đang xử lý
      </Button>
    );
  }
  return null;
}
