import { z } from 'zod';

interface FieldConfig {
  type: string;
  label?: string;
  placeholder?: string;
  required?: boolean;
  readonly?: boolean;
  options?: Array<{ value: string; label: string }>;
  props?: Record<string, unknown>;
  validation?: {
    min?: number;
    max?: number;
    pattern?: string;
    minLength?: number;
    maxLength?: number;
  };
}

// Create Zod schema for a field configuration
export function createFieldSchema(config: FieldConfig, fieldName?: string): z.ZodType {
  const fieldLabel = config.label || "Field";

  // Smart detection for array fields based on field name
  const isLikelyArrayField = fieldName && (
    fieldName.toLowerCase().includes('tag') ||
    fieldName.toLowerCase().includes('list') ||
    fieldName.toLowerCase().includes('array')
  );

  // Override type for likely array fields
  if (isLikelyArrayField && config.type !== "array") {
    const schema = z.union([
      z.array(z.string()),
      z.string().transform((str) => {
        // Transform comma-separated string to array
        if (str.trim() === "") return [];
        return str.split(",").map(item => item.trim()).filter(item => item.length > 0);
      })
    ], {
      message: `${fieldLabel} must be an array or comma-separated string`,
    });

    return config.required ? schema : schema.optional();
  }

  switch (config.type) {
    case "number": {
      let schema = z.coerce.number({
        message: `${fieldLabel} must be a valid number`,
      });

      if (config.validation?.min !== undefined) {
        schema = schema.min(config.validation.min, `${fieldLabel} must be at least ${config.validation.min}`);
      }
      if (config.validation?.max !== undefined) {
        schema = schema.max(config.validation.max, `${fieldLabel} must be at most ${config.validation.max}`);
      }

      return config.required ? schema : schema.optional();
    }

    case "text":
    case "input": {
      let schema = z.string({
        message: `${fieldLabel} must be text`,
      });

      if (config.validation?.minLength !== undefined) {
        schema = schema.min(config.validation.minLength, `${fieldLabel} must be at least ${config.validation.minLength} characters`);
      }
      if (config.validation?.maxLength !== undefined) {
        schema = schema.max(config.validation.maxLength, `${fieldLabel} must be at most ${config.validation.maxLength} characters`);
      }
      if (config.validation?.pattern) {
        schema = schema.regex(new RegExp(config.validation.pattern), `${fieldLabel} format is invalid`);
      }

      return config.required ? schema : schema.optional();
    }

    case "textarea": {
      let schema = z.string({
        message: `${fieldLabel} must be text`,
      });

      if (config.validation?.minLength !== undefined) {
        schema = schema.min(config.validation.minLength, `${fieldLabel} must be at least ${config.validation.minLength} characters`);
      }
      if (config.validation?.maxLength !== undefined) {
        schema = schema.max(config.validation.maxLength, `${fieldLabel} must be at most ${config.validation.maxLength} characters`);
      }

      return config.required ? schema : schema.optional();
    }

    case "email": {
      const schema = z.string({
        message: `${fieldLabel} must be text`,
      }).email(`${fieldLabel} must be a valid email address`);

      return config.required ? schema : schema.optional();
    }

    case "select": {
      if (!config.options || config.options.length === 0) {
        console.warn(`Select field '${fieldLabel}' has no options defined`);
        return config.required ? z.string() : z.string().optional();
      }

      const validValues = config.options.map(opt => opt.value);
      const enumSchema = z.enum(validValues as [string, ...string[]], {
        message: `${fieldLabel} must be one of the available options`,
      });

      return config.required ? enumSchema : enumSchema.optional();
    }

    case "checkbox": {
      const schema = z.boolean({
        message: `${fieldLabel} must be true or false`,
      });

      return config.required ? schema : schema.optional();
    }

    case "date": {
      const schema = z.union([
        z.string().datetime(),
        z.date(),
        z.string().refine((val) => !isNaN(Date.parse(val)), {
          message: `${fieldLabel} must be a valid date`,
        }),
      ], {
        message: `${fieldLabel} must be a valid date`,
      });

      return config.required ? schema : schema.optional();
    }

    case "array": {
      const schema = z.union([
        z.array(z.string()),
        z.string().transform((str) => {
          // Transform comma-separated string to array
          if (str.trim() === "") return [];
          return str.split(",").map(item => item.trim()).filter(item => item.length > 0);
        })
      ], {
        message: `${fieldLabel} must be an array or comma-separated string`,
      });

      return config.required ? schema : schema.optional();
    }

    default: {
      console.warn(`Unknown field type: ${config.type}`);
      return config.required ? z.unknown() : z.unknown().optional();
    }
  }
}

// Create complete validation schema for form data
export function createFormSchema(componentConfigs: Record<string, unknown>): z.ZodObject<Record<string, z.ZodType>> {
  const schemaShape: Record<string, z.ZodType> = {};

  Object.entries(componentConfigs).forEach(([fieldName, config]) => {
    if (config && typeof config === 'object') {
      schemaShape[fieldName] = createFieldSchema(config as FieldConfig, fieldName);
    }
  });

  return z.object(schemaShape);
}

// Validate field value using Zod
export function validateFieldValueWithZod(value: unknown, config: FieldConfig, fieldName?: string): string | null {
  try {
    const schema = createFieldSchema(config, fieldName);
    schema.parse(value);
    return null; // No error
  } catch (error) {
    if (error instanceof z.ZodError) {
      return error.issues[0]?.message || "Validation failed";
    }
    return "Validation failed";
  }
}

// Validate entire form data using Zod
export function validateFormDataWithZod(
  data: Record<string, unknown>,
  componentConfigs: Record<string, unknown>
): { success: true; data: Record<string, unknown> } | { success: false; errors: Record<string, string> } {
  try {
    const schema = createFormSchema(componentConfigs);
    const result = schema.parse(data);
    return { success: true, data: result };
  } catch (error) {
    if (error instanceof z.ZodError) {
      const errors: Record<string, string> = {};
      error.issues.forEach((err: z.ZodIssue) => {
        if (err.path.length > 0) {
          const fieldName = err.path[0] as string;
          errors[fieldName] = err.message;
        }
      });
      return { success: false, errors };
    }
    return { success: false, errors: { general: "Validation failed" } };
  }
}

// Helper function to get default value for a field type
export function getDefaultFieldValue(config: FieldConfig): unknown {
  switch (config.type) {
    case "checkbox":
      return false;
    case "number":
      return 0;
    case "select":
      return config.options?.[0]?.value || "";
    case "date":
      return null;
    case "array":
      return [];
    default:
      return "";
  }
}

// Helper function to validate field value
export function validateFieldValue(value: unknown, config: FieldConfig): string | null {
  // Required field validation
  if (config.required) {
    if (value === null || value === undefined || value === "") {
      return `${config.label || "Field"} is required`;
    }
  }

  // Skip further validation if field is empty and not required
  if (!value && !config.required) {
    return null;
  }

  // Type-specific validation for numbers (always validate, even without config.validation)
  if (config.type === "number") {
    // Handle null values from invalid input
    if (value === null) {
      return "Please enter a valid number";
    }

    const numValue = Number(value);
    // Check if the value is not a valid number
    if (isNaN(numValue) || !isFinite(numValue)) {
      return "Please enter a valid number";
    }

    // Additional validation if config exists
    if (config.validation) {
      const { min, max } = config.validation;
      if (min !== undefined && numValue < min) {
        return `Value must be at least ${min}`;
      }
      if (max !== undefined && numValue > max) {
        return `Value must be at most ${max}`;
      }
    }
  }

  // Other type-specific validation
  if (config.validation) {
    const { minLength, maxLength, pattern } = config.validation;

    if (config.type === "input" || config.type === "text" || config.type === "textarea" || config.type === "email") {
      const stringValue = String(value);
      if (minLength !== undefined && stringValue.length < minLength) {
        return `Must be at least ${minLength} characters`;
      }
      if (maxLength !== undefined && stringValue.length > maxLength) {
        return `Must be at most ${maxLength} characters`;
      }
      if (pattern && !new RegExp(pattern).test(stringValue)) {
        return "Invalid format";
      }
    }

    if (config.type === "email") {
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!emailRegex.test(String(value))) {
        return "Invalid email format";
      }
    }
  }

  return null;
}

// Helper function to sanitize data before sending to API
export function sanitizeFormData(
  data: Record<string, unknown>,
  componentConfigs: Record<string, unknown>
): Record<string, unknown> {
  const sanitized: Record<string, unknown> = {};

  Object.entries(data).forEach(([fieldName, value]) => {
    const config = componentConfigs[fieldName] as FieldConfig | undefined;

    if (!config) {
      sanitized[fieldName] = value;
      return;
    }

    // If the value is already an array (from Zod transformation), preserve it
    if (Array.isArray(value)) {
      sanitized[fieldName] = value;
      return;
    }

    // Handle null/undefined values based on field type
    if (value === null || value === undefined || value === "") {
      // For array fields, use empty array instead of null
      if (config.type === "array" || fieldName.toLowerCase().includes('tag') || fieldName.toLowerCase().includes('list') || fieldName.toLowerCase().includes('array')) {
        sanitized[fieldName] = [];
        return;
      }
      // For other fields, use null
      sanitized[fieldName] = null;
      return;
    }

    // Type-specific sanitization
    switch (config.type) {
      case "number": {
        const numValue = Number(value);
        if (isNaN(numValue) || !isFinite(numValue) || value === null) {
          // Don't sanitize invalid numbers - let validation catch this
          sanitized[fieldName] = null;
        } else {
          sanitized[fieldName] = numValue;
        }
        break;
      }

      case "checkbox": {
        sanitized[fieldName] = Boolean(value);
        break;
      }

      case "date": {
        if (typeof value === "string" && value.trim()) {
          // Validate date format
          const date = new Date(value);
          if (!isNaN(date.getTime())) {
            sanitized[fieldName] = value;
          } else {
            sanitized[fieldName] = null;
          }
        } else {
          sanitized[fieldName] = null;
        }
        break;
      }

      case "select": {
        // Ensure the value is one of the valid options
        const validValues = config.options?.map(opt => opt.value) || [];
        if (validValues.length > 0 && !validValues.includes(String(value))) {
          sanitized[fieldName] = null;
        } else {
          sanitized[fieldName] = String(value);
        }
        break;
      }

      case "array": {
        // Handle array fields
        if (Array.isArray(value)) {
          sanitized[fieldName] = value;
        } else if (value === null || value === undefined || value === "") {
          sanitized[fieldName] = [];
        } else if (typeof value === "string") {
          // Handle comma-separated string input for arrays
          const trimmed = value.trim();
          if (trimmed === "") {
            sanitized[fieldName] = [];
          } else {
            // Split by comma and clean up each item
            sanitized[fieldName] = trimmed
              .split(",")
              .map(item => item.trim())
              .filter(item => item.length > 0);
          }
        } else {
          // Convert single value to array
          sanitized[fieldName] = [value];
        }
        break;
      }

      default: {
        // For text fields, convert to string - but check for potential array fields
        if (fieldName.toLowerCase().includes('tag') || fieldName.toLowerCase().includes('list') || fieldName.toLowerCase().includes('array')) {
          if (typeof value === "string" && value.includes(',')) {
            // Treat as comma-separated array
            sanitized[fieldName] = value.split(',').map(item => item.trim()).filter(item => item.length > 0);
          } else if (typeof value === "string" && value.trim()) {
            // Single value to array
            sanitized[fieldName] = [value.trim()];
          } else {
            sanitized[fieldName] = String(value);
          }
        } else {
          // For text fields, convert to string
          sanitized[fieldName] = String(value);
        }
        break;
      }
    }
  });

  return sanitized;
}
