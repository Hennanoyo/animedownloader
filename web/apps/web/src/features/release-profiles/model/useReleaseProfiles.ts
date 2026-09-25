import {
  queryOptions,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import {
  activateParserProfile,
  compareParserProfile,
  createDraftFromObservation,
  createParserDraft,
  createParserSample,
  deleteParserSample,
  getParserHealth,
  getParserProfiles,
  getParserSamples,
  updateParserProfile,
  validateParserProfile,
  type ParserRuleInput,
} from "../../../entities/release/api/releaseProfiles";

export function parserProfilesQueryOptions(groupId: string) {
  return queryOptions({
    queryKey: ["release-parser-profiles", groupId] as const,
    queryFn: ({ signal }) => getParserProfiles(groupId, signal),
    enabled: groupId.length > 0,
  });
}

export function parserSamplesQueryOptions(groupId: string) {
  return queryOptions({
    queryKey: ["release-parser-samples", groupId] as const,
    queryFn: ({ signal }) => getParserSamples(groupId, signal),
    enabled: groupId.length > 0,
  });
}

export function parserHealthQueryOptions(profileId: string) {
  return queryOptions({
    queryKey: ["release-parser-health", profileId] as const,
    queryFn: ({ signal }) => getParserHealth(profileId, signal),
    enabled: profileId.length > 0,
  });
}

export function parserComparisonQueryOptions(profileId: string) {
  return queryOptions({
    queryKey: ["release-parser-comparison", profileId] as const,
    queryFn: ({ signal }) => compareParserProfile(profileId, signal),
    enabled: profileId.length > 0,
  });
}

export function useParserProfiles(groupId: string) {
  return useQuery(parserProfilesQueryOptions(groupId));
}

export function useParserSamples(groupId: string) {
  return useQuery(parserSamplesQueryOptions(groupId));
}

export function useParserHealth(profileId: string) {
  return useQuery(parserHealthQueryOptions(profileId));
}

export function useParserComparison(profileId: string) {
  return useQuery(parserComparisonQueryOptions(profileId));
}

export function useCreateParserDraft() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ groupId }: { groupId: string }) => createParserDraft(groupId),
    onSuccess: async (profile) => {
      await client.invalidateQueries({
        queryKey: ["release-parser-profiles", profile.release_group_id],
      });
      await client.invalidateQueries({ queryKey: ["release-groups"] });
    },
  });
}

export function useUpdateParserProfile() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({
      profileId,
      rules,
    }: {
      profileId: string;
      rules: ParserRuleInput[];
    }) => updateParserProfile(profileId, rules),
    onSuccess: async (profile) => {
      await Promise.all([
        client.invalidateQueries({
          queryKey: ["release-parser-profiles", profile.release_group_id],
        }),
        client.invalidateQueries({
          queryKey: ["release-parser-comparison", profile.id],
        }),
        client.invalidateQueries({
          queryKey: ["release-parser-health", profile.id],
        }),
      ]);
    },
  });
}

export function useCreateParserSample() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({
      groupId,
      title,
      source,
    }: {
      groupId: string;
      title: string;
      source: string;
    }) => createParserSample(groupId, { title, source }),
    onSuccess: async (sample) => {
      await Promise.all([
        client.invalidateQueries({
          queryKey: ["release-parser-samples", sample.release_group_id],
        }),
        client.invalidateQueries({ queryKey: ["release-parser-profiles"] }),
      ]);
    },
  });
}

export function useDeleteParserSample() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ sampleId }: { sampleId: string; groupId: string }) =>
      deleteParserSample(sampleId),
    onSuccess: async (_value, variables) => {
      await Promise.all([
        client.invalidateQueries({
          queryKey: ["release-parser-samples", variables.groupId],
        }),
        client.invalidateQueries({ queryKey: ["release-parser-profiles"] }),
      ]);
    },
  });
}

export function useValidateParserProfile() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ profileId }: { profileId: string }) =>
      validateParserProfile(profileId),
    onSuccess: async (_value, variables) => {
      await client.invalidateQueries({
        queryKey: ["release-parser-health", variables.profileId],
      });
    },
  });
}

export function useActivateParserProfile() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ profileId }: { profileId: string }) =>
      activateParserProfile(profileId),
    onSuccess: async (profile) => {
      await Promise.all([
        client.invalidateQueries({
          queryKey: ["release-parser-profiles", profile.release_group_id],
        }),
        client.invalidateQueries({
          queryKey: ["release-groups"],
        }),
      ]);
    },
  });
}

export function useCreateDraftFromObservation() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ observationId }: { observationId: string }) =>
      createDraftFromObservation(observationId),
    onSuccess: async (profile) => {
      await Promise.all([
        client.invalidateQueries({
          queryKey: ["release-parser-profiles", profile.release_group_id],
        }),
        client.invalidateQueries({
          queryKey: ["release-parser-samples", profile.release_group_id],
        }),
      ]);
    },
  });
}
