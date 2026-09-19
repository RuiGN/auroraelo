import React, { useState } from 'react';
import { View, Text, TouchableOpacity, ScrollView, StyleSheet, Alert } from 'react-native';

export function HomeScreen() {
  const [selectedMood, setSelectedMood] = useState('CALM');

  const moods = [
    { id: 'RADIANT', label: 'Radiante', emoji: '✨' },
    { id: 'CALM', label: 'Calmo', emoji: '🌿' },
    { id: 'ANXIOUS', label: 'Ansioso', emoji: '⚡' },
    { id: 'LOW', label: 'Para Baixo', emoji: '🌧️' },
  ];

  const handleMoodSelect = (id: string) => {
    setSelectedMood(id);
    Alert.alert('Humor Registrado', 'Seu estado emocional foi sincronizado com seu histórico de bem-estar.');
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      {/* Header */}
      <View style={styles.header}>
        <View>
          <Text style={styles.brand}>Aurora Mind</Text>
          <Text style={styles.tagline}>Mindfulness, Psicoeducação & TCC</Text>
        </View>
        <View style={styles.streakBadge}>
          <Text style={styles.streakText}>🔥 14 Dias</Text>
        </View>
      </View>

      <!-- Daily Mood Card -->
      <View style={styles.moodCard}>
        <Text style={styles.moodQuestion}>Como você está se sentindo hoje?</Text>
        <View style={styles.moodRow}>
          {moods.map((m) => (
            <TouchableOpacity
              key={m.id}
              style={[styles.moodBtn, selectedMood === m.id && styles.moodBtnActive]}
              onPress={() => handleMoodSelect(m.id)}
            >
              <Text style={styles.moodEmoji}>{m.emoji}</Text>
              <Text style={[styles.moodLabel, selectedMood === m.id && styles.moodLabelActive]}>
                {m.label}
              </Text>
            </TouchableOpacity>
          ))}
        </View>
      </View>

      <!-- Box Breathing Feature -->
      <TouchableOpacity
        style={styles.breathingCard}
        onPress={() => Alert.alert('Iniciando Exercício', 'Respire no ritmo 4-4-4-4: inspire 4s, segure 4s, expire 4s, pause 4s.')}
      >
        <View>
          <Text style={styles.cardBadge}>EXERCÍCIO CLÍNICO</Text>
          <Text style={styles.breathingTitle}>Respiração Guiada 4-4-4-4</Text>
          <Text style={styles.breathingDesc}>Alívio rápido de ansiedade e taquicardia</Text>
        </View>
        <View style={styles.breathingCircle}>
          <Text style={styles.breathingSecs}>4s</Text>
        </View>
      </TouchableOpacity>

      <!-- CBT Thought Diary -->
      <TouchableOpacity
        style={styles.cbtCard}
        onPress={() => Alert.alert('Diário de Pensamentos TCC', 'Identifique pensamentos automáticos e reestruture distorções cognitivas.')}
      >
        <Text style={styles.cbtTitle}>📝 Diário de Pensamentos (TCC)</Text>
        <Text style={styles.cbtDesc}>Reestruture pensamentos automáticos disfuncionais</Text>
      </TouchableOpacity>

      <!-- In-App Purchase Premium Card -->
      <View style={styles.premiumCard}>
        <View style={styles.premiumHeader}>
          <Text style={styles.premiumTitle}>Aurora Mind Plus</Text>
          <Text style={styles.premiumPrice}>R$ 29,90/mês</Text>
        </View>
        <Text style={styles.premiumDesc}>
          Desbloqueie testes diagnósticos validados (PHQ-9 e GAD-7) e exporte relatórios clínicos semanais em PDF para seu médico.
        </Text>
        <TouchableOpacity
          style={styles.premiumBtn}
          onPress={() => Alert.alert('Assinatura Aurora Mind Plus', 'Iniciando teste gratuito de 7 dias via loja de aplicativos.')}
        >
          <Text style={styles.premiumBtnText}>Experimentar 7 Dias Grátis</Text>
        </TouchableOpacity>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#07172c' },
  content: { padding: 20, paddingBottom: 40 },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 },
  brand: { fontSize: 22, fontWeight: '900', color: '#ffffff' },
  tagline: { fontSize: 11, color: '#38bdf8', fontWeight: '600' },
  streakBadge: { backgroundColor: 'rgba(245, 158, 11, 0.2)', paddingHorizontal: 10, paddingVertical: 4, borderRadius: 20, borderWidth: 1, borderColor: 'rgba(245, 158, 11, 0.4)' },
  streakText: { color: '#fcd34d', fontSize: 12, fontWeight: '800' },
  moodCard: { backgroundColor: 'rgba(255, 255, 255, 0.07)', padding: 18, borderRadius: 24, marginBottom: 20, borderWidth: 1, borderColor: 'rgba(255, 255, 255, 0.1)' },
  moodQuestion: { color: '#ffffff', fontSize: 13, fontWeight: '700', marginBottom: 14 },
  moodRow: { flexDirection: 'row', justifyContent: 'space-between' },
  moodBtn: { flex: 1, alignItems: 'center', paddingVertical: 10, marginHorizontal: 4, borderRadius: 16, backgroundColor: 'rgba(255, 255, 255, 0.05)' },
  moodBtnActive: { backgroundColor: 'rgba(6, 182, 212, 0.25)', borderWidth: 1, borderColor: '#22d3ee' },
  moodEmoji: { fontSize: 24 },
  moodLabel: { color: '#94a3b8', fontSize: 10, marginTop: 4, fontWeight: '600' },
  moodLabelActive: { color: '#22d3ee', fontWeight: '800' },
  breathingCard: { backgroundColor: '#0c2d48', padding: 18, borderRadius: 24, marginBottom: 20, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', borderWidth: 1, borderColor: 'rgba(6, 182, 212, 0.4)' },
  cardBadge: { color: '#38bdf8', fontSize: 10, fontWeight: '800', letterSpacing: 1 },
  breathingTitle: { color: '#ffffff', fontSize: 15, fontWeight: '800', marginTop: 2 },
  breathingDesc: { color: '#bae6fd', fontSize: 11, marginTop: 2, maxWidth: 200 },
  breathingCircle: { width: 48, height: 48, borderRadius: 24, borderWidth: 2, borderColor: '#22d3ee', borderStyle: 'dashed', alignItems: 'center', justifyContent: 'center' },
  breathingSecs: { color: '#ffffff', fontWeight: '800', fontSize: 12 },
  cbtCard: { backgroundColor: 'rgba(255, 255, 255, 0.05)', padding: 16, borderRadius: 20, marginBottom: 20, borderWidth: 1, borderColor: 'rgba(255, 255, 255, 0.1)' },
  cbtTitle: { color: '#ffffff', fontSize: 13, fontWeight: '700' },
  cbtDesc: { color: '#94a3b8', fontSize: 11, marginTop: 2 },
  premiumCard: { backgroundColor: '#1e1b4b', padding: 18, borderRadius: 24, borderWidth: 1, borderColor: '#8b5cf6' },
  premiumHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 },
  premiumTitle: { color: '#ffffff', fontSize: 16, fontWeight: '900' },
  premiumPrice: { color: '#c4b5fd', fontSize: 12, fontWeight: '800' },
  premiumDesc: { color: '#e0e7ff', fontSize: 11, lineHeight: 16, marginBottom: 14 },
  premiumBtn: { backgroundColor: '#8b5cf6', paddingVertical: 12, borderRadius: 16, alignItems: 'center' },
  premiumBtnText: { color: '#ffffff', fontWeight: '800', fontSize: 13 }
});
