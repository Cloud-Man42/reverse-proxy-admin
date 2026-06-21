const STEPS = [
  "Overview",
  "Domain",
  "Upstream",
  "Options",
  "Recommended",
  "Preview",
  "Create",
];

interface WizardStepperProps {
  currentStep: number;
}

export function WizardStepper({ currentStep }: WizardStepperProps) {
  return (
    <ol className="flex flex-wrap gap-2">
      {STEPS.map((label, index) => {
        const stepNumber = index + 1;
        const active = stepNumber === currentStep;
        const completed = stepNumber < currentStep;
        return (
          <li
            key={label}
            className={`rounded-full px-3 py-1 text-xs font-medium ${
              active
                ? "bg-accent text-white"
                : completed
                  ? "bg-emerald-500/20 text-emerald-200"
                  : "bg-white/10 text-white/60"
            }`}
          >
            {stepNumber}. {label}
          </li>
        );
      })}
    </ol>
  );
}

export const WIZARD_STEP_COUNT = STEPS.length;
