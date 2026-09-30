export default function SectionHeader({ title, description, action }) {
  return (
    <div className="flex items-start justify-between mb-3">
      <div>
        <h2 className="text-sm font-semibold text-text-primary">{title}</h2>
        {description && <p className="text-xs text-text-secondary mt-0.5">{description}</p>}
      </div>
      {action}
    </div>
  );
}
