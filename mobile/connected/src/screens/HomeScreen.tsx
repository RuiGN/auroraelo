import React, { useState, useEffect } from 'react';
import { View, Text, TouchableOpacity, ScrollView, Alert, StyleSheet, Image } from 'react-native';
import { AuroraApiService } from '../services/api';
import { colors } from '../theme/tokens';

export function HomeScreen({ navigation }: any) {
  const [data, setData] = useState<any>(null);
  const [meds, setMeds] = useState([
    { id: 1, name: 'Escitalopram 15mg', time: '08:00', taken: true },
    { id: 2, name: 'Quetiapina 25mg', time: '21:00', taken: false },
  ]);

  useEffect(() => {
    AuroraApiService.getPatientSummary()
      .then((res) => {
        if (res.success) setData(res.data);
      })
      .catch(() => {});
  }, []);

  const toggleMed = async (id: number) => {
    setMeds((prev) =>
      prev.map((m) => (m.id === id ? { ...m, taken: !m.taken } : m))
    );
    await AuroraApiService.logMedication(id, true);
  };

  const handleSOS = async () => {
    Alert.alert(
      'Acionar SOS Crise Psiquiátrica?',
      'O plantão médico 24h da clínica e sua rede de apoio serão notificados imediatamente com sua localização.',
      [
        { text: 'Cancelar', style: 'cancel' },
        {
          text: 'Confirmar SOS',
          style: 'destructive',
          onPress: async () => {
            const res = await AuroraApiService.triggerSOS();
            Alert.alert('Alerta Enviado', res.instructions || 'Plantão 24h notificado.');
          },
        },
      ]
    );
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      {/* Header */}
      <View style={styles.header}>
        <View>
          <Text style={styles.greeting}>Olá, Mariana</Text>
          <Text style={styles.subtitle}>Seu plano terapêutico está em dia</Text>
        </View>
        <View style={styles.statusBadge}>
          <View style={styles.statusDot} />
          <Text style={styles.statusText}>Conectado</Text>
        </View>
      </View>

      <!-- Telehealth Card -->
      <View style={styles.teleCard}>
        <View style={styles.teleHeader}>
          <Text style={styles.teleBadge}>● Teleconsulta Hoje, 14:30</Text>
          <Text style={styles.teleCountdown}>12 min</Text>
        </View>
        <Text style={styles.doctorName}>Dr. Marcelo Arantes • Psiquiatra</Text>
        <Text style={styles.doctorCrm}>CRM/SP 148.920 • Reavaliação e receita</Text>
        <TouchableOpacity style={styles.joinBtn} onPress={() => Alert.alert('Conectando à sala criptografada...')}>
          <Text style={styles.joinBtnText}>Acessar Teleconsulta HD</Text>
        </TouchableOpacity>
      </View>

      <!-- Medications Card -->
      <View style={styles.medCard}>
        <Text style={styles.sectionTitle}>MEDICAMENTOS DE HOJE</Text>
        {meds.map((med) => (
          <TouchableOpacity key={med.id} style={styles.medItem} onPress={() => toggleMed(med.id)}>
            <Text style={[styles.medName, med.taken && styles.medTaken]}>
              {med.name} • {med.time} {med.taken ? '✓ (Tomado)' : '(Pendente)'}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      <!-- Emergency SOS Button -->
      <TouchableOpacity style={styles.sosButton} onPress={handleSOS}>
        <Text style={styles.sosButtonText}>🚨 Botão de Ajuda Imediata / SOS 24h</Text>
        <Text style={styles.sosSubtext}>Plantão Aurora Elo & CVV 188</Text>
      </TouchableOpacity>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f8fafc' },
  content: { padding: 20, paddingBottom: 40 },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 },
  greeting: { fontSize: 22, fontWeight: '800', color: colors.aurora[900] },
  subtitle: { fontSize: 13, color: '#64748b' },
  statusBadge: { flexDirection: 'row', alignItems: 'center', backgroundColor: colors.healing[50], paddingHorizontal: 10, paddingVertical: 4, borderRadius: 20 },
  statusDot: { width: 6, height: 6, borderRadius: 3, backgroundColor: colors.healing[500], marginRight: 6 },
  statusText: { fontSize: 11, fontWeight: '700', color: colors.healing[600] },
  teleCard: { backgroundColor: colors.aurora[900], padding: 18, borderRadius: 20, marginBottom: 20 },
  teleHeader: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 8 },
  teleBadge: { color: colors.elo[400], fontSize: 12, fontWeight: '700' },
  teleCountdown: { color: '#ffffff', fontSize: 11, backgroundColor: 'rgba(255,255,255,0.1)', paddingHorizontal: 6, borderRadius: 6 },
  doctorName: { color: '#ffffff', fontSize: 14, fontWeight: '700' },
  doctorCrm: { color: colors.aurora[200], fontSize: 11, marginBottom: 12 },
  joinBtn: { backgroundColor: colors.elo[500], paddingVertical: 10, borderRadius: 12, alignItems: 'center' },
  joinBtnText: { color: colors.aurora[950], fontWeight: '800', fontSize: 13 },
  medCard: { backgroundColor: '#ffffff', padding: 16, borderRadius: 20, marginBottom: 20, borderWidth: 1, borderColor: '#e2e8f0' },
  sectionTitle: { fontSize: 11, fontWeight: '800', color: '#64748b', marginBottom: 10 },
  medItem: { paddingVertical: 10, borderBottomWidth: 1, borderBottomColor: '#f1f5f9' },
  medName: { fontSize: 13, color: '#1e293b', fontWeight: '600' },
  medTaken: { textDecorationLine: 'line-through', color: '#94a3b8' },
  sosButton: { backgroundColor: colors.crisis[500], padding: 16, borderRadius: 20, alignItems: 'center', shadowColor: colors.crisis[500], shadowOpacity: 0.3, shadowRadius: 10 },
  sosButtonText: { color: '#ffffff', fontWeight: '800', fontSize: 14 },
  sosSubtext: { color: '#ffe4e6', fontSize: 11, marginTop: 2 }
});
