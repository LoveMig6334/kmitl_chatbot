import { Label as RadixLabel } from "radix-ui";
import { cn } from "@/lib/cn";

export function Label({
  className,
  ...props
}: React.ComponentProps<typeof RadixLabel.Root>) {
  return (
    <RadixLabel.Root
      className={cn("text-sm font-medium text-fg select-none", className)}
      {...props}
    />
  );
}
