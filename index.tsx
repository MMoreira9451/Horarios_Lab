import React, { useEffect, useState } from 'react';
import { StyleSheet, Text, View, TextInput, Button, FlatList, Platform, TouchableOpacity, ScrollView, RefreshControl } from 'react-native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import AsyncStorage from '@react-native-async-storage/async-storage';
import QRCode from 'react-native-qrcode-svg';
import { StatusBar } from 'expo-status-bar';
import { NavigationIndependentTree } from '@react-navigation/native';

const Tab = createBottomTabNavigator();

const API_BASE = Platform.OS === 'web'
  ? 'http://localhost:8081'
  : 'http://10.0.5.63:8081'; // Reemplaza si usas Expo Go en móvil

// ----------------- Generador de QR -----------------
// Función QRGenerator mejorada para manejar correctamente la expiración y renovación
function QRGenerator() {
  const [name, setName] = useState('');
  const [surname, setSurname] = useState('');
  const [email, setEmail] = useState('');
  const [savedUsers, setSavedUsers] = useState([]);
  const [selectedUser, setSelectedUser] = useState(null);
  const [autoRenewal, setAutoRenewal] = useState(false);
  const [renewInterval, setRenewInterval] = useState(null);
  const [qrExpired, setQrExpired] = useState(false);
  
  useEffect(() => {
    loadSavedUsers();
    return () => {
      if (renewInterval) clearInterval(renewInterval);
    };
  }, []);

  const loadSavedUsers = async () => {
    try {
      const storedUsers = await AsyncStorage.getItem('savedUsers');
      if (storedUsers !== null) {
        setSavedUsers(JSON.parse(storedUsers));
      }
    } catch (error) {
      console.error('Error cargando usuarios:', error);
    }
  };

  const saveUser = async () => {
    if (name.trim() === '' || surname.trim() === '' || email.trim() === '' || !email.includes('@')) {
      alert('Por favor, ingresa datos válidos');
      return;
    }

    const timestamp = Date.now();
    const userData = { 
      name, 
      surname, 
      email, 
      timestamp, 
      expired: false 
    };

    try {
      const newUsers = [...savedUsers, userData];
      await AsyncStorage.setItem('savedUsers', JSON.stringify(newUsers));
      setSavedUsers(newUsers);
      setSelectedUser(userData);
      setQrExpired(false);

      // Limpiar cualquier intervalo existente
      if (renewInterval) {
        clearInterval(renewInterval);
        setRenewInterval(null);
      }

      // Configurar autorrenovación o expiración del QR
      if (autoRenewal) {
        const interval = setInterval(() => {
          const newTimestamp = Date.now();
          setSelectedUser(prevUser => ({
            ...prevUser,
            timestamp: newTimestamp,
            expired: false
          }));
        }, 14000); // Renovar cada 14 segundos
        setRenewInterval(interval);
      } else {
        // Configurar expiración después de 15 segundos
        setTimeout(() => {
          setQrExpired(true);
          setSelectedUser(prevUser => ({
            ...prevUser,
            expired: true
          }));
        }, 15000);
      }

      setName('');
      setSurname('');
      setEmail('');
    } catch (error) {
      console.error('Error guardando usuario:', error);
    }
  };

  const toggleAutoRenewal = () => {
    const newAutoRenewal = !autoRenewal;
    setAutoRenewal(newAutoRenewal);
    
    // Limpiar cualquier intervalo existente
    if (renewInterval) {
      clearInterval(renewInterval);
      setRenewInterval(null);
    }

    if (selectedUser) {
      if (newAutoRenewal) {
        // Activar renovación automática
        const interval = setInterval(() => {
          const newTimestamp = Date.now();
          setSelectedUser(prevUser => ({
            ...prevUser,
            timestamp: newTimestamp,
            expired: false
          }));
          setQrExpired(false);
        }, 14000);
        setRenewInterval(interval);
      } else if (qrExpired) {
        // Ya está expirado, mantenerlo así
        setSelectedUser(prevUser => ({
          ...prevUser,
          expired: true
        }));
      } else {
        // Configurar expiración después de 15 segundos
        setTimeout(() => {
          setQrExpired(true);
          setSelectedUser(prevUser => {
            if (prevUser) {
              return {
                ...prevUser,
                expired: true
              };
            }
            return null;
          });
        }, 15000);
      }
    }
  };

  const selectSavedUser = (user) => {
    // Limpiar cualquier intervalo existente
    if (renewInterval) {
      clearInterval(renewInterval);
      setRenewInterval(null);
    }
    
    setName(user.name);
    setSurname(user.surname);
    setEmail(user.email);
    
    // Al seleccionar un usuario existente, generamos un nuevo QR con timestamp actual
    const timestamp = Date.now();
    const updatedUser = { ...user, timestamp, expired: false };
    setSelectedUser(updatedUser);
    setQrExpired(false);
    
    // Configuramos la expiración o auto-renovación
    if (autoRenewal) {
      const interval = setInterval(() => {
        const newTimestamp = Date.now();
        setSelectedUser(prevUser => ({
          ...prevUser,
          timestamp: newTimestamp,
          expired: false
        }));
      }, 14000);
      setRenewInterval(interval);
    } else {
      setTimeout(() => {
        setQrExpired(true);
        setSelectedUser(prevUser => ({
          ...prevUser,
          expired: true
        }));
      }, 15000);
    }
  };

  // Generar el valor del QR como un objeto JSON válido
  // Generar el valor del QR como un objeto JSON válido con codificación adecuada
  const generateQrValue = () => {
    if (!selectedUser) return JSON.stringify({});
  
    // Ensure proper string encoding by removing trailing spaces and normalizing text
    const sanitizedUser = {
      name: selectedUser.name.trim(),
      surname: selectedUser.surname.trim(),
      email: selectedUser.email.trim(),
      timestamp: selectedUser.timestamp
    };
  
    // Add additional properties based on state
    if (qrExpired && !autoRenewal) {
      return JSON.stringify({
        ...sanitizedUser,
        expired: true,
        status: "EXPIRED"
      });
    }
  
    if (autoRenewal) {
      return JSON.stringify({
        ...sanitizedUser,
        timestamp: Date.now(),
        autoRenewal: true,
        status: "VALID"
      });
    }
  
    return JSON.stringify({
      ...sanitizedUser,
      status: "VALID"
    });
  };
  return (
    <View style={styles.container}>
      <Text style={styles.title}>Generador de QR</Text>
      <TextInput style={styles.input} placeholder="Nombre" value={name} onChangeText={setName} />
      <TextInput style={styles.input} placeholder="Apellido" value={surname} onChangeText={setSurname} />
      <TextInput style={styles.input} placeholder="Email" value={email} onChangeText={setEmail} keyboardType="email-address" autoCapitalize="none" />
      
      <View style={styles.optionsRow}>
        <Button title="Generar QR" onPress={saveUser} />
        <TouchableOpacity onPress={toggleAutoRenewal} style={[styles.checkboxContainer, autoRenewal && styles.checkboxChecked]}>
          <Text style={styles.checkboxText}>Auto-renovar QR</Text>
        </TouchableOpacity>
      </View>

      {savedUsers.length > 0 && (
        <ScrollView horizontal style={styles.userList}>
          {savedUsers.map((user, idx) => (
            <TouchableOpacity 
              key={idx} 
              style={styles.userItem}
              onPress={() => selectSavedUser(user)}
            >
              <Text style={styles.userItemText}>{user.name} {user.surname}</Text>
            </TouchableOpacity>
          ))}
        </ScrollView>
      )}

      {selectedUser && (
        <View style={styles.qrContainer}>
          <Text style={[
            styles.userText, 
            (qrExpired && !autoRenewal) ? styles.expiredText : styles.validText
          ]}>
            {(qrExpired && !autoRenewal) 
              ? 'QR Expirado' 
              : `${selectedUser.name} ${selectedUser.surname} - ${selectedUser.email}`
            }
          </Text>
          <QRCode
            value={generateQrValue()}
            size={200}
            backgroundColor="white"
            color={(qrExpired && !autoRenewal) ? "#cccccc" : "black"}
          />
          {autoRenewal && (
            <Text style={styles.renewalText}>QR con renovación automática activa</Text>
          )}
          {!autoRenewal && !qrExpired && (
            <Text style={styles.expirationText}>
              Este QR expirará en 15 segundos
            </Text>
          )}
        </View>
      )}
      <StatusBar style="auto" />
    </View>
  );
}

// ----------------- Registros del Día -----------------
function RegistrosScreen() {
  const [registros, setRegistros] = useState([]);
  const [refreshing, setRefreshing] = useState(false);
  const [filtroPersona, setFiltroPersona] = useState(null);

  const loadRegistros = () => {
    setRefreshing(true);
    fetch(`${API_BASE}/registros_hoy`)
      .then(res => res.json())
      .then(data => {
        setRegistros(data);
        setRefreshing(false);
      })
      .catch(err => {
        console.error(err);
        setRefreshing(false);
      });
  };

  useEffect(() => {
    loadRegistros();
    // Actualizar cada 5 minutos
    const interval = setInterval(loadRegistros, 300000);
    return () => clearInterval(interval);
  }, []);

  const onRefresh = () => {
    loadRegistros();
  };

  const getUniquePersonas = () => {
    const uniqueEmails = [...new Set(registros.map(item => item.email))];
    return uniqueEmails.map(email => {
      const persona = registros.find(r => r.email === email);
      return {
        email: email,
        nombre: `${persona.nombre} ${persona.apellido}`
      };
    });
  };

  const filteredRegistros = filtroPersona 
    ? registros.filter(item => item.email === filtroPersona)
    : registros;

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Registros de Hoy</Text>
      
      <ScrollView horizontal style={styles.filterContainer}>
        <TouchableOpacity 
          style={[styles.filterButton, filtroPersona === null && styles.filterActive]} 
          onPress={() => setFiltroPersona(null)}
        >
          <Text style={styles.filterText}>Todos</Text>
        </TouchableOpacity>
        
        {getUniquePersonas().map((persona, idx) => (
          <TouchableOpacity 
            key={idx} 
            style={[styles.filterButton, filtroPersona === persona.email && styles.filterActive]}
            onPress={() => setFiltroPersona(persona.email)}
          >
            <Text style={styles.filterText}>{persona.nombre}</Text>
          </TouchableOpacity>
        ))}
      </ScrollView>
      
      <FlatList
        data={filteredRegistros}
        keyExtractor={(item, index) => `${item.id || index}`}
        renderItem={({ item }) => (
          <View style={styles.registroItem}>
            <Text style={styles.registroNombre}>{item.nombre} {item.apellido}</Text>
            <Text style={styles.registroHora}>{item.hora}</Text>
            <Text style={styles.registroTipo}>
              {getRegistroTipo(item, filteredRegistros)}
            </Text>
          </View>
        )}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
        }
      />

      <Text style={styles.lastUpdate}>
        Última actualización: {new Date().toLocaleTimeString()}
      </Text>
    </View>
  );
}

// Función para determinar si un registro es entrada o salida
const getRegistroTipo = (registro, todosRegistros) => {
  // Ordenar registros por hora para esta persona
  const registrosPersona = todosRegistros
    .filter(r => r.email === registro.email)
    .sort((a, b) => {
      const timeA = new Date(`2000-01-01T${a.hora}`);
      const timeB = new Date(`2000-01-01T${b.hora}`);
      return timeA - timeB;
    });
  
  // Determinar posición del registro actual
  const idx = registrosPersona.findIndex(r => 
    r.id === registro.id || 
    (r.hora === registro.hora && r.nombre === registro.nombre)
  );
  
  // Si es impar, es salida; si es par, es entrada
  return idx % 2 === 0 ? 'Entrada' : 'Salida';
};

// ----------------- Cumplimiento -----------------
// For the CumplimientoScreen component in index.tsx

function CumplimientoScreen() {
  const [cumplimiento, setCumplimiento] = useState([]);
  const [refreshing, setRefreshing] = useState(false);
  const [view, setView] = useState('resumen'); // 'resumen' o 'detalle'

  const loadCumplimiento = () => {
    setRefreshing(true);
    fetch(`${API_BASE}/cumplimiento`)
      .then(res => res.json())
      .then(data => {
        setCumplimiento(data);
        setRefreshing(false);
      })
      .catch(err => {
        console.error(err);
        setRefreshing(false);
      });
  };

  useEffect(() => {
    loadCumplimiento();
    // Actualizar cada 5 minutos
    const interval = setInterval(loadCumplimiento, 300000);
    return () => clearInterval(interval);
  }, []);

  const onRefresh = () => {
    loadCumplimiento();
  };

  // Calcular estadísticas de cumplimiento basado en bloques
  const stats = {
    total: cumplimiento.length,
    cumpliendo: cumplimiento.filter(item => 
      item.estado === 'Cumpliendo').length,
    incompleto: cumplimiento.filter(item => 
      item.estado === 'Incompleto').length,
    ausente: cumplimiento.filter(item => 
      item.estado === 'Ausente').length,
    retrasado: cumplimiento.filter(item => 
      item.estado === 'Retrasado').length,
    noAplica: cumplimiento.filter(item => 
      item.estado === 'No Aplica').length
  };

  // Colores según estado
  const getStatusColor = (estado) => {
    switch(estado) {
      case 'Cumpliendo': return '#4CAF50';
      case 'Incompleto': return '#FF9800';
      case 'Ausente': return '#F44336';
      case 'Retrasado': return '#FFC107';
      case 'No Aplica': return '#9E9E9E';
      default: return '#9E9E9E';
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Cumplimiento de Horarios</Text>
      
      <View style={styles.viewToggle}>
        <TouchableOpacity 
          style={[styles.toggleButton, view === 'resumen' && styles.toggleActive]}
          onPress={() => setView('resumen')}
        >
          <Text style={styles.toggleText}>Resumen</Text>
        </TouchableOpacity>
        <TouchableOpacity 
          style={[styles.toggleButton, view === 'detalle' && styles.toggleActive]}
          onPress={() => setView('detalle')}
        >
          <Text style={styles.toggleText}>Detalle</Text>
        </TouchableOpacity>
      </View>
      
      {view === 'resumen' ? (
        <View style={styles.statsContainer}>
          <View style={styles.statCard}>
            <Text style={styles.statValue}>{stats.cumpliendo}</Text>
            <Text style={styles.statLabel}>Cumpliendo</Text>
            <View style={[styles.statusIndicator, {backgroundColor: '#4CAF50'}]} />
          </View>
          <View style={styles.statCard}>
            <Text style={styles.statValue}>{stats.retrasado}</Text>
            <Text style={styles.statLabel}>Retrasados</Text>
            <View style={[styles.statusIndicator, {backgroundColor: '#FFC107'}]} />
          </View>
          <View style={styles.statCard}>
            <Text style={styles.statValue}>{stats.incompleto}</Text>
            <Text style={styles.statLabel}>Incompletos</Text>
            <View style={[styles.statusIndicator, {backgroundColor: '#FF9800'}]} />
          </View>
          <View style={styles.statCard}>
            <Text style={styles.statValue}>{stats.ausente}</Text>
            <Text style={styles.statLabel}>Ausentes</Text>
            <View style={[styles.statusIndicator, {backgroundColor: '#F44336'}]} />
          </View>
          <View style={styles.statCard}>
            <Text style={styles.statValue}>{stats.noAplica}</Text>
            <Text style={styles.statLabel}>No Aplica</Text>
            <View style={[styles.statusIndicator, {backgroundColor: '#9E9E9E'}]} />
          </View>
        </View>
      ) : (
        <FlatList
          data={cumplimiento}
          keyExtractor={(item, index) => `${item.email}-${index}`}
          renderItem={({ item }) => (
            <View style={styles.cumplimientoItem}>
              <Text style={styles.cumplimientoNombre}>{item.nombre} {item.apellido}</Text>
              <View style={[
                styles.cumplimientoEstado, 
                {backgroundColor: getStatusColor(item.estado)}
              ]}>
                <Text style={styles.cumplimientoEstadoText}>{item.estado}</Text>
              </View>
              {item.bloques && item.bloques.length > 0 ? (
                <View style={styles.bloquesContainer}>
                  {item.bloques.map((bloque, idx) => (
                    <View key={idx} style={styles.bloqueItem}>
                      <Text style={styles.bloqueHora}>
                        {bloque.inicio} - {bloque.fin}
                      </Text>
                      <Text style={styles.bloqueEstado}>
                        {bloque.estado || 'Pendiente'}
                      </Text>
                    </View>
                  ))}
                </View>
              ) : item.estado === 'No Aplica' && (
                <Text style={styles.noScheduleText}>
                  Sin horario programado para hoy
                </Text>
              )}
            </View>
          )}
          refreshControl={
            <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
          }
        />
      )}
      
      <Text style={styles.lastUpdate}>
        Última actualización: {new Date().toLocaleTimeString()}
      </Text>
    </View>
  );
}

// ------------- Componente para Horas Acumuladas -------------
function HorasAcumuladasScreen() {
  const [horasData, setHorasData] = useState([]);  // Initialize as empty array
  const [refreshing, setRefreshing] = useState(false);
  const [sortBy, setSortBy] = useState('horas'); // 'horas' o 'nombre'

  const loadHorasAcumuladas = () => {
    setRefreshing(true);
    fetch(`${API_BASE}/horas_acumuladas`)
      .then(res => res.json())
      .then(data => {
        // Ensure data is an array before setting state
        if (Array.isArray(data)) {
          setHorasData(data);
        } else {
          console.error('Expected array from API but got:', data);
          setHorasData([]); // Set empty array as fallback
        }
        setRefreshing(false);
      })
      .catch(err => {
        console.error('Error loading horas acumuladas:', err);
        setRefreshing(false);
      });
  };

  useEffect(() => {
    loadHorasAcumuladas();
    // Actualizar cada 15 minutos
    const interval = setInterval(loadHorasAcumuladas, 900000);
    return () => clearInterval(interval);
  }, []);

  const onRefresh = () => {
    loadHorasAcumuladas();
  };

  // Ordenar datos - Ensure we're dealing with an array before sorting
  const sortedData = (Array.isArray(horasData) ? [...horasData] : [])
    .sort((a, b) => {
      if (sortBy === 'horas') {
        return b.horas_totales - a.horas_totales; // Mayor a menor
      } else {
        return a.nombre.localeCompare(b.nombre); // Alfabético
      }
    });

  // Add the rest of the component as before...
  // ...
  return (
    <View style={styles.container}>
      <Text style={styles.title}>Horas Acumuladas</Text>
      
      <View style={styles.sortButtons}>
        <TouchableOpacity 
          style={[styles.sortButton, sortBy === 'horas' && styles.sortActive]}
          onPress={() => setSortBy('horas')}
        >
          <Text style={styles.sortButtonText}>Por Horas</Text>
        </TouchableOpacity>
        <TouchableOpacity 
          style={[styles.sortButton, sortBy === 'nombre' && styles.sortActive]}
          onPress={() => setSortBy('nombre')}
        >
          <Text style={styles.sortButtonText}>Por Nombre</Text>
        </TouchableOpacity>
      </View>
      
      <FlatList
        data={sortedData}
        keyExtractor={(item) => item.email}
        renderItem={({ item }) => (
          <View style={styles.horasItem}>
            <View style={styles.horasInfo}>
              <Text style={styles.horasNombre}>{item.nombre} {item.apellido}</Text>
              <Text style={styles.horasEmail}>{item.email}</Text>
            </View>
            <View style={styles.horasStats}>
              <View style={styles.horaStat}>
                <Text style={styles.horasStatValue}>{item.horas_totales}</Text>
                <Text style={styles.horasStatLabel}>Horas</Text>
              </View>
              <View style={styles.horaStat}>
                <Text style={styles.horasStatValue}>{item.dias_asistidos}</Text>
                <Text style={styles.horasStatLabel}>Días</Text>
              </View>
            </View>
          </View>
        )}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
        }
      />
      
      <Text style={styles.lastUpdate}>
        Última actualización: {new Date().toLocaleTimeString()}
      </Text>
    </View>
  );
}

// Add this to your styles object:
const additionalStyles = {
  noScheduleText: {
    fontStyle: 'italic',
    color: '#757575',
    marginTop: 8,
  }
};

// Make sure to add additionalStyles to your existing styles object
// styles = StyleSheet.create({...existingStyles, ...additionalStyles});

// ----------------- Componente para crear navegación de tabs -----------------
const TabNavigator = () => {
  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        tabBarIcon: ({ focused, color, size }) => {
          let iconName;
          if (route.name === 'Generar QR') {
            iconName = '🔄';
          } else if (route.name === 'Registros') {
            iconName = '📝';
          } else if (route.name === 'Cumplimiento') {
            iconName = '✅';
          } else if (route.name === 'Horas') {
            iconName = '⏱️';
          }
          return <Text style={{fontSize: 24}}>{iconName}</Text>;
        },
      })}
    >
      <Tab.Screen name="Generar QR" component={QRGenerator} />
      <Tab.Screen name="Registros" component={RegistrosScreen} />
      <Tab.Screen name="Cumplimiento" component={CumplimientoScreen} />
      <Tab.Screen name="Horas" component={HorasAcumuladasScreen} />
    </Tab.Navigator>
  );
};

// ----------------- App Principal -----------------
// Para uso con Expo Router, usamos NavigationIndependentTree
export default function App() {
  return (
    <NavigationIndependentTree>
      <TabNavigator />
    </NavigationIndependentTree>
  );
}

// ----------------- Estilos -----------------
const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
    padding: 20,
  },
  title: {
    fontSize: 22,
    fontWeight: 'bold',
    marginBottom: 20,
    textAlign: 'center',
  },
  input: {
    height: 50,
    borderWidth: 1,
    borderColor: '#ddd',
    borderRadius: 5,
    marginBottom: 10,
    paddingHorizontal: 10,
    backgroundColor: 'white',
  },
  optionsRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 15,
  },
  checkboxContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 10,
    borderWidth: 1,
    borderColor: '#ddd',
    borderRadius: 5,
    backgroundColor: 'white',
  },
  checkboxChecked: {
    backgroundColor: '#e6f7ff',
    borderColor: '#1890ff',
  },
  checkboxText: {
    marginLeft: 5,
  },
  userList: {
    maxHeight: 50,
    marginVertical: 10,
  },
  userItem: {
    padding: 10,
    marginRight: 10,
    backgroundColor: '#e6f7ff',
    borderRadius: 5,
  },
  userItemText: {
    color: '#1890ff',
  },
  qrContainer: {
    alignItems: 'center',
    marginTop: 20,
    padding: 20,
    backgroundColor: 'white',
    borderRadius: 10,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 3,
    elevation: 2,
  },
  userText: {
    fontSize: 16,
    marginBottom: 15,
    fontWeight: '500',
  },
  expiredText: {
    color: '#ff4d4f',
  },
  validText: {
    color: '#52c41a',
  },
  renewalText: {
    marginTop: 10,
    color: '#1890ff',
    fontStyle: 'italic',
  },
  filterContainer: {
    marginBottom: 10,
    maxHeight: 50,
  },
  filterButton: {
    paddingHorizontal: 15,
    paddingVertical: 8,
    marginRight: 10,
    backgroundColor: 'white',
    borderRadius: 20,
    borderWidth: 1,
    borderColor: '#ddd',
  },
  filterActive: {
    backgroundColor: '#1890ff',
    borderColor: '#1890ff',
  },
  filterText: {
    color: '#333',
  },
  registroItem: {
    padding: 15,
    marginBottom: 10,
    backgroundColor: 'white',
    borderRadius: 5,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  registroNombre: {
    flex: 2,
    fontWeight: '500',
  },
  registroHora: {
    flex: 1,
    textAlign: 'center',
  },
  registroTipo: {
    flex: 1,
    textAlign: 'right',
    fontWeight: '500',
  },
  lastUpdate: {
    textAlign: 'center',
    fontSize: 12,
    color: '#999',
    marginTop: 10,
  },
  viewToggle: {
    flexDirection: 'row',
    marginBottom: 15,
    justifyContent: 'center',
  },
  toggleButton: {
    paddingHorizontal: 20,
    paddingVertical: 10,
    backgroundColor: 'white',
    marginHorizontal: 5,
    borderRadius: 5,
    borderWidth: 1,
    borderColor: '#ddd',
  },
  toggleActive: {
    backgroundColor: '#1890ff',
    borderColor: '#1890ff',
  },
  toggleText: {
    color: '#333',
  },
  statsContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
  },
  statCard: {
    width: '48%',
    backgroundColor: 'white',
    padding: 15,
    marginBottom: 15,
    borderRadius: 10,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 2,
    elevation: 1,
    position: 'relative',
  },
  statValue: {
    fontSize: 32,
    fontWeight: 'bold',
  },
  statLabel: {
    fontSize: 14,
    color: '#666',
  },
  statusIndicator: {
    position: 'absolute',
    top: 0,
    left: 0,
    width: 10,
    height: '100%',
    borderTopLeftRadius: 10,
    borderBottomLeftRadius: 10,
  },
  cumplimientoItem: {
    padding: 15,
    marginBottom: 10,
    backgroundColor: 'white',
    borderRadius: 5,
  },
  cumplimientoNombre: {
    fontSize: 16,
    fontWeight: '500',
    marginBottom: 5,
  },
  cumplimientoEstado: {
    alignSelf: 'flex-start',
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 15,
    marginBottom: 10,
  },
  cumplimientoEstadoText: {
    color: 'white',
    fontWeight: '500',
  },
  bloquesContainer: {
    marginTop: 5,
  },
  bloqueItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 5,
    borderBottomWidth: 1,
    borderBottomColor: '#eee',
  },
  bloqueHora: {
    color: '#666',
  },
  bloqueEstado: {
    fontWeight: '500',
  },
  // Añadir estos estilos al objeto styles existente
  sortButtons: {
    flexDirection: 'row',
    justifyContent: 'center',
    marginBottom: 15,
  },
  sortButton: {
    paddingHorizontal: 15,
    paddingVertical: 8,
    marginHorizontal: 10,
    backgroundColor: 'white',
    borderRadius: 20,
    borderWidth: 1,
    borderColor: '#ddd',
  },
  sortActive: {
    backgroundColor: '#1890ff',
    borderColor: '#1890ff',
  },
  sortButtonText: {
    color: '#333',
  },
  horasItem: {
    padding: 15,
    marginBottom: 10,
    backgroundColor: 'white',
    borderRadius: 5,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 1,
    elevation: 1,
  },
  horasInfo: {
    flex: 2,
  },
  horasNombre: {
    fontSize: 16,
    fontWeight: '500',
  },
  horasEmail: {
    fontSize: 12,
    color: '#666',
  },
  horasStats: {
    flex: 1,
    flexDirection: 'row',
    justifyContent: 'space-around',
  },
  horaStat: {
    alignItems: 'center',
  },
  horasStatValue: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#1890ff',
  },
  horasStatLabel: {
    fontSize: 12,
    color: '#666',
  },
});