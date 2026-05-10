export type ClassValue = string | false | null | undefined | ClassValue[];

export function cn(...values: ClassValue[]): string {
  const classes: string[] = [];

  function collect(value: ClassValue): void {
    if (!value) {
      return;
    }
    if (Array.isArray(value)) {
      value.forEach(collect);
      return;
    }
    classes.push(value);
  }

  values.forEach(collect);
  return classes.join(" ");
}
