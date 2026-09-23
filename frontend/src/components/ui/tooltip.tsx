import * as React from "react"
import { cn } from "@/lib/utils"

const TooltipContext = React.createContext<{
    open: boolean;
    setOpen: React.Dispatch<React.SetStateAction<boolean>>;
} | null>(null);

const TooltipProvider = ({ children }: { children: React.ReactNode }) => <>{children}</>

const Tooltip = ({ children }: { children: React.ReactNode, delayDuration?: number }) => {
    const [open, setOpen] = React.useState(false)

    return (
        <TooltipContext.Provider value={{ open, setOpen }}>
            <div
                className="relative inline-flex"
                onMouseEnter={() => setOpen(true)}
                onMouseLeave={() => setOpen(false)}
            >
                {children}
            </div>
        </TooltipContext.Provider>
    )
}

const TooltipTrigger = React.forwardRef<HTMLElement, React.HTMLAttributes<HTMLElement>>(({ className, children, ...props }, _ref) => {
    return (
        <div className={cn("cursor-pointer", className)} {...props}>
            {children}
        </div>
    )
})
TooltipTrigger.displayName = "TooltipTrigger"

const TooltipContent = React.forwardRef<
    HTMLDivElement,
    React.HTMLAttributes<HTMLDivElement> & { sideOffset?: number }
>(({ className, sideOffset = 4, ...props }, ref) => {
    const context = React.useContext(TooltipContext)
    if (!context?.open) return null

    return (
        <div
            ref={ref}
            className={cn(
                "z-50 overflow-hidden rounded-md border border-slate-700 bg-slate-900 px-3 py-1.5 text-xs text-slate-200 shadow-md animate-in fade-in-0 zoom-in-95 absolute bottom-full left-1/2 -translate-x-1/2 mb-2 whitespace-nowrap",
                className
            )}
            {...props}
        />
    )
})
TooltipContent.displayName = "TooltipContent"

export { Tooltip, TooltipTrigger, TooltipContent, TooltipProvider }
