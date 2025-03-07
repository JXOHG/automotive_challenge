import { forwardRef } from "react"

const Progress = forwardRef(({ value = 0, className = "", ...props }, ref) => {
  return (
    <div
      ref={ref}
      role="progressbar"
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={value}
      className={`relative h-4 w-full overflow-hidden rounded-full bg-gray-100 ${className}`}
      {...props}
    >
      <div
        className="h-full w-full flex-1 bg-primary transition-all bg-blue-600"
        style={{ transform: `translateX(-${100 - (value || 0)}%)` }}
      />
    </div>
  )
})
Progress.displayName = "Progress"

export { Progress }

