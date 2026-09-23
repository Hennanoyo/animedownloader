import { useForm } from "@tanstack/react-form";
import {
  Button,
  Form,
  Input,
  Label,
  ListBox,
  ListBoxItem,
  Popover,
  Select,
  SelectValue,
  Text,
  TextField,
} from "react-aria-components";
import type {
  Season,
  Weekday,
} from "../../../entities/anime/model/types";
import type { Anime } from "../../../entities/anime/model/types";
import { useUpdateAnime } from "../model/useEditAnime";
import {
  animeEditFormSchema,
  type AnimeEditFormValues,
} from "../model/schema";
import styles from "./AnimeEditForm.module.scss";

const seasons: Array<{ value: Season; label: string }> = [
  { value: "winter", label: "Winter" },
  { value: "spring", label: "Spring" },
  { value: "summer", label: "Summer" },
  { value: "fall", label: "Fall" },
];

const weekdays: Array<{ value: Weekday; label: string }> = [
  { value: "monday", label: "Monday" },
  { value: "tuesday", label: "Tuesday" },
  { value: "wednesday", label: "Wednesday" },
  { value: "thursday", label: "Thursday" },
  { value: "friday", label: "Friday" },
  { value: "saturday", label: "Saturday" },
  { value: "sunday", label: "Sunday" },
];

interface Props {
  anime: Anime;
  onCancel: () => void;
  onSaved: () => void;
}

export default function AnimeEditForm({ anime, onCancel, onSaved }: Props) {
  const mutation = useUpdateAnime(anime.id);

  const form = useForm({
    defaultValues: {
      title: anime.title,
      year: anime.year,
      season: anime.season,
      weekday: anime.weekday,
      air_time: anime.air_time?.slice(0, 5) ?? "",
      timezone: anime.timezone,
    } satisfies AnimeEditFormValues,
    validators: {
      onSubmit: animeEditFormSchema,
    },
    onSubmit: async ({ value }) => {
      await mutation.mutateAsync({
        title: value.title.trim(),
        year: value.year,
        season: value.season,
        weekday: value.weekday,
        air_time: value.air_time || null,
        timezone: value.timezone.trim(),
      });
      onSaved();
    },
  });

  return (
    <Form
      className={styles.form}
      onSubmit={(event) => {
        event.preventDefault();
        void form.handleSubmit();
      }}
    >
      <div className={styles.grid}>
        <form.Field name="title">
          {(field) => (
            <TextField
              className={styles.field}
              isRequired
              isInvalid={!field.state.meta.isValid}
              validationBehavior="aria"
            >
              <Label>Title</Label>
              <Input
                value={field.state.value}
                onBlur={field.handleBlur}
                onChange={(event) => field.handleChange(event.target.value)}
              />
              {!field.state.meta.isValid ? (
                <Text slot="errorMessage" className={styles.fieldError}>
                  {field.state.meta.errors.map(String).join(", ")}
                </Text>
              ) : null}
            </TextField>
          )}
        </form.Field>

        <form.Field name="year">
          {(field) => (
            <TextField
              className={styles.field}
              isRequired
              isInvalid={!field.state.meta.isValid}
              validationBehavior="aria"
            >
              <Label>Year</Label>
              <Input
                type="number"
                inputMode="numeric"
                value={String(field.state.value)}
                onBlur={field.handleBlur}
                onChange={(event) =>
                  field.handleChange(Number(event.target.value))
                }
              />
              {!field.state.meta.isValid ? (
                <Text slot="errorMessage" className={styles.fieldError}>
                  {field.state.meta.errors.map(String).join(", ")}
                </Text>
              ) : null}
            </TextField>
          )}
        </form.Field>

        <form.Field name="season">
          {(field) => (
            <Select
              className={styles.field}
              selectedKey={field.state.value}
              onSelectionChange={(key) =>
                field.handleChange(String(key) as Season)
              }
            >
              <Label>Season</Label>
              <Button className={styles.selectButton} type="button">
                <SelectValue />
              </Button>
              <Popover className={styles.popover}>
                <ListBox>
                  {seasons.map((option) => (
                    <ListBoxItem id={option.value} key={option.value}>
                      {option.label}
                    </ListBoxItem>
                  ))}
                </ListBox>
              </Popover>
            </Select>
          )}
        </form.Field>

        <form.Field name="weekday">
          {(field) => (
            <Select
              className={styles.field}
              selectedKey={field.state.value}
              onSelectionChange={(key) =>
                field.handleChange(String(key) as Weekday)
              }
            >
              <Label>Weekday</Label>
              <Button className={styles.selectButton} type="button">
                <SelectValue />
              </Button>
              <Popover className={styles.popover}>
                <ListBox>
                  {weekdays.map((option) => (
                    <ListBoxItem id={option.value} key={option.value}>
                      {option.label}
                    </ListBoxItem>
                  ))}
                </ListBox>
              </Popover>
            </Select>
          )}
        </form.Field>

        <form.Field name="air_time">
          {(field) => (
            <TextField
              className={styles.field}
              isInvalid={!field.state.meta.isValid}
              validationBehavior="aria"
            >
              <Label>Air time</Label>
              <Input
                type="time"
                value={field.state.value}
                onBlur={field.handleBlur}
                onChange={(event) => field.handleChange(event.target.value)}
              />
              {!field.state.meta.isValid ? (
                <Text slot="errorMessage" className={styles.fieldError}>
                  {field.state.meta.errors.map(String).join(", ")}
                </Text>
              ) : null}
            </TextField>
          )}
        </form.Field>

        <form.Field name="timezone">
          {(field) => (
            <TextField
              className={styles.field}
              isInvalid={!field.state.meta.isValid}
              validationBehavior="aria"
            >
              <Label>Timezone</Label>
              <Input
                value={field.state.value}
                onBlur={field.handleBlur}
                onChange={(event) => field.handleChange(event.target.value)}
              />
              {!field.state.meta.isValid ? (
                <Text slot="errorMessage" className={styles.fieldError}>
                  {field.state.meta.errors.map(String).join(", ")}
                </Text>
              ) : null}
            </TextField>
          )}
        </form.Field>
      </div>

      {mutation.isError ? (
        <p className={styles.formError} role="alert">
          Failed to update anime: {mutation.error.message}
        </p>
      ) : null}

      <div className={styles.actions}>
        <Button
          type="button"
          className={styles.cancelButton}
          onPress={onCancel}
        >
          Cancel
        </Button>
        <Button
          type="submit"
          className={styles.primaryButton}
          isDisabled={form.state.isSubmitting || mutation.isPending}
        >
          {mutation.isPending ? "Saving..." : "Save changes"}
        </Button>
      </div>
    </Form>
  );
}
