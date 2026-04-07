interface TimestampProps {
  value: string | null;
}

export function Timestamp({ value }: TimestampProps) {
  if (!value) {
    return <span>-</span>;
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return <span>{value}</span>;
  }

  return <span>{date.toLocaleString()}</span>;
}
