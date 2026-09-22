import { useForm } from "@tanstack/react-form";
import { Button, Form, Input, Label, Text, TextField } from "react-aria-components";
import { z } from "zod";
import styles from "./ReleaseSearchForm.module.scss";

const searchFormSchema = z.object({
  query: z
    .string()
    .trim()
    .min(1, "Enter a search term.")
    .max(200, "Search term must be 200 characters or fewer."),
});

interface ReleaseSearchFormProps {
  initialQuery: string;
  onSearch: (query: string) => void;
  embedded?: boolean;
}

export default function ReleaseSearchForm({
  initialQuery,
  onSearch,
  embedded = false,
}: ReleaseSearchFormProps) {
  const form = useForm({
    defaultValues: {
      query: initialQuery,
    },
    validators: {
      onSubmit: searchFormSchema,
    },
    onSubmit: ({ value }) => {
      onSearch(value.query.trim());
    },
  });

  const content = (
    <>
      <form.Field name="query">
        {(field) => {
          const hasError = field.state.meta.errors.length > 0;

          return (
            <TextField
              isRequired
              isInvalid={hasError}
              validationBehavior="aria"
            >
              <Label className={styles.label}>Search Nyaa releases</Label>
              <Input
                className={styles.input}
                name={field.name}
                type="search"
                value={field.state.value}
                onBlur={field.handleBlur}
                onChange={(event) => field.handleChange(event.target.value)}
                placeholder="e.g. Frieren 1080p"
              />
              <Text slot="description" className={styles.description}>
                Searches Nyaa's RSS feed and returns the latest matching releases.
              </Text>
              {hasError ? (
                <Text slot="errorMessage" className={styles.error}>
                  {String(field.state.meta.errors[0])}
                </Text>
              ) : null}
            </TextField>
          );
        }}
      </form.Field>
      <Button
        className={styles.button}
        type={embedded ? "button" : "submit"}
        onPress={embedded ? () => void form.handleSubmit() : undefined}
        isDisabled={form.state.isSubmitting}
      >
        {form.state.isSubmitting ? "Searching..." : "Search"}
      </Button>
    </>
  );

  if (embedded) {
    return <div className={styles.form}>{content}</div>;
  }

  return (
    <Form
      className={styles.form}
      onSubmit={(event) => {
        event.preventDefault();
        void form.handleSubmit();
      }}
    >
      {content}
    </Form>
  );
}
