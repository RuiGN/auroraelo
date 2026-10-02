import { useNavigation } from "@react-navigation/native";
import { NativeStackNavigationProp } from "@react-navigation/native-stack";
import { RootStackParamList } from "./types";

export type RootNavigation = NativeStackNavigationProp<RootStackParamList>;

/** Navegação tipada: todas as telas de detalhe vivem na pilha raiz, acima das abas. */
export function useNav(): RootNavigation {
  return useNavigation<RootNavigation>();
}
